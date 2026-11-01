from contextlib import closing
from datetime import datetime, timezone
import re
import uuid
from fastapi import HTTPException
from . import action_security, session_security as security
from .database import now
from .identity import transaction, hash_password, audit
from .identity_schemas import EmailInput, RegisterInput
from .mfa_settings import check_password


def profile(db, user):
    with closing(db.connect()) as conn:
        row = dict(conn.execute('SELECT id,name,email,role,status,created_at FROM users WHERE id=?', (user.id,)).fetchone())
        extra = conn.execute('SELECT phone,phone_verified_at,kyc_status FROM customer_profiles WHERE user_id=?', (user.id,)).fetchone()
        row.update(dict(extra) if extra else {'phone': '', 'phone_verified_at': None, 'kyc_status': 'UNVERIFIED'})
        return row


def change_profile(db, user, field, value, password):
    check_password(db, user, password)
    recipient = None
    if field == 'email':
        try:
            value = EmailInput(email=value).email
        except ValueError:
            raise HTTPException(422, 'Enter a valid email address.')
        recipient = value
    elif field == 'phone':
        if not re.fullmatch(r'\+?[0-9]{9,15}', value):
            raise HTTPException(422, 'Enter 9 to 15 digits, with an optional + prefix.')
        recipient = value  # Simulated SMS delivery uses the same local developer outbox.
    elif field == 'password':
        if not 15 <= len(value) <= 128:
            raise HTTPException(422, 'Use a password of 15 to 128 characters.')
    elif field == 'name':
        try:
            value = RegisterInput.validate_name(value)
        except ValueError:
            raise HTTPException(422, 'Enter a valid display name.')
        if len(value) > 80:
            raise HTTPException(422, 'Display name is too long.')
    else:
        raise HTTPException(422, 'Unsupported profile field.')
    action_security.limit(db, user)
    with transaction(db) as conn:
        if field == 'email' and conn.execute('SELECT 1 FROM users WHERE email=?', (value,)).fetchone():
            raise HTTPException(409, 'This email is not available.')
        payload = {'password_hash': hash_password(value)} if field == 'password' else {'value': value}
        return action_security.create(conn, user, 'PROFILE_' + field.upper(), payload, recipient)


def apply_profile_change(conn, user, kind, payload, stamp):
    iso = datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec='seconds')
    if kind == 'PROFILE_PASSWORD':
        conn.execute('UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE id=?', (payload['password_hash'], user.id))
        security.revoke_user(conn, user.id, stamp, 'PASSWORD_CHANGED')
        conn.execute('UPDATE identity_tokens SET consumed_at=? WHERE user_id=? AND consumed_at IS NULL', (stamp, user.id))
    elif kind == 'PROFILE_EMAIL':
        if conn.execute('SELECT 1 FROM users WHERE email=?', (payload['value'],)).fetchone():
            raise HTTPException(409, 'This email is no longer available.')
        old = conn.execute('SELECT email FROM users WHERE id=?', (user.id,)).fetchone()[0]
        conn.execute('UPDATE users SET email=? WHERE id=?', (payload['value'], user.id))
        for challenge in conn.execute('SELECT id FROM mfa_challenges WHERE user_id=? AND consumed_at IS NULL', (user.id,)).fetchall():
            security.consume_challenge(conn, challenge[0], stamp)
        conn.execute('UPDATE identity_tokens SET consumed_at=? WHERE user_id=? AND consumed_at IS NULL', (stamp, user.id))
        conn.execute('''INSERT INTO dev_outbox (id,user_id,recipient,kind,created_at,body) VALUES (?,?,?,?,?,?)''',
                     (uuid.uuid4().hex, user.id, old, 'EMAIL_CHANGED_NOTICE', stamp, 'Your NovaBank email was changed. Contact support if this was unexpected.'))
    elif kind == 'PROFILE_PHONE':
        conn.execute('''INSERT INTO customer_profiles (user_id,phone,phone_verified_at) VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone,phone_verified_at=excluded.phone_verified_at''', (user.id, payload['value'], iso))
    elif kind == 'PROFILE_NAME':
        conn.execute('UPDATE users SET name=? WHERE id=?', (payload['value'], user.id))
    else:
        raise HTTPException(400, 'Unsupported change.')
    audit(conn, user.id, kind, stamp)
    action_security.notify(conn, user.id, 'SECURITY', 'Profile updated', kind.replace('_', ' ').title(), iso)
    return {'message': 'Profile updated.' if kind != 'PROFILE_PASSWORD' else 'Password updated. Sign in again.',
            'sign_in_required': kind == 'PROFILE_PASSWORD'}


def accounts(db, user):
    with closing(db.connect()) as conn:
        return {'items': [dict(r) for r in conn.execute('''SELECT a.*,COALESCE(l.nickname,'Payment account') AS nickname
            FROM accounts a LEFT JOIN account_labels l ON l.account_id=a.id WHERE a.owner_id=? ORDER BY a.id''', (user.id,))]}


def account_label(db, user, account_id, nickname):
    with transaction(db) as conn:
        if not conn.execute('SELECT 1 FROM accounts WHERE id=? AND owner_id=?', (account_id, user.id)).fetchone():
            raise HTTPException(404, 'Account not found.')
        conn.execute('INSERT INTO account_labels VALUES (?,?) ON CONFLICT(account_id) DO UPDATE SET nickname=excluded.nickname', (account_id, nickname.strip()))
    return {'message': 'Account nickname saved.'}


def beneficiaries(db, user, q=''):
    with closing(db.connect()) as conn:
        needle = '%' + q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        return {'items': [dict(r) for r in conn.execute('''SELECT * FROM beneficiaries WHERE owner_id=?
            AND (nickname LIKE ? ESCAPE '\\' OR holder_name LIKE ? ESCAPE '\\' OR account_id LIKE ? ESCAPE '\\')
            ORDER BY created_at DESC,id''', (user.id, needle, needle, needle))]}


def edit_beneficiary(db, user, beneficiary_id, nickname):
    if not nickname.strip():
        raise HTTPException(422, 'Enter a recipient nickname.')
    with transaction(db) as conn:
        if not conn.execute('UPDATE beneficiaries SET nickname=? WHERE id=? AND owner_id=?',
                            (nickname.strip(), beneficiary_id, user.id)).rowcount:
            raise HTTPException(404, 'Recipient not found.')
        return dict(conn.execute('SELECT * FROM beneficiaries WHERE id=? AND owner_id=?', (beneficiary_id, user.id)).fetchone())


def lookup_recipient(db, user, account_id, bank):
    from .recipient_security import limit
    limit(db, user)
    with closing(db.connect()) as conn:
        bank = bank.strip()
        if bank.lower() in ('novabank', 'nova', 'nvb'):
            bank = 'NovaBank'
            account_id = account_id.upper()
            row = conn.execute("SELECT holder_name FROM accounts WHERE id=? AND status='ACTIVE'", (account_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'Active recipient account not found.')
            name = row[0]
        else:
            if bank not in ('Demo Bank A', 'Demo Bank B') or not re.fullmatch(r'[0-9]{6,20}', account_id):
                raise HTTPException(422, 'Use a supported simulated bank and 6 to 20 account digits.')
            name = 'SIMULATED RECIPIENT ' + account_id[-4:]
        return {'account_id': account_id, 'bank': bank, 'holder_name': name}


def save_beneficiary(db, user, account_id, bank, nickname):
    recipient = lookup_recipient(db, user, account_id, bank)
    account_id, bank, name = recipient['account_id'], recipient['bank'], recipient['holder_name']
    with transaction(db) as conn:
        if conn.execute('SELECT 1 FROM beneficiaries WHERE owner_id=? AND bank=? AND account_id=?', (user.id, bank, account_id)).fetchone():
            raise HTTPException(409, 'Recipient is already saved.')
        result = dict(id=uuid.uuid4().hex, owner_id=user.id, account_id=account_id, bank=bank, holder_name=name,
                      nickname=nickname.strip(), trust_level='untrusted', created_at=now())
        conn.execute('INSERT INTO beneficiaries VALUES (:id,:owner_id,:account_id,:bank,:holder_name,:nickname,:trust_level,:created_at)', result)
        return result


def delete_beneficiary(db, user, beneficiary_id):
    with transaction(db) as conn:
        if not conn.execute('DELETE FROM beneficiaries WHERE id=? AND owner_id=?', (beneficiary_id, user.id)).rowcount:
            raise HTTPException(404, 'Recipient not found.')
    return {'message': 'Recipient removed.'}
