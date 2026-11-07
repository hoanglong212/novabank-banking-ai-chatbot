"""Session-bound, single-use confirmations for customer-initiated actions."""
import hashlib
import hmac
import json
import secrets
import uuid
from fastapi import HTTPException
from . import auth, session_security as security
from .identity import digest, quota, transaction
from .mfa_settings import PIN_MARK, TOTP_MARK, setup_required, transaction_factor, verify_factor


def otp_hash(challenge, code):
    return hmac.new(auth.SECRET.encode(), f'action:{challenge}:{code}'.encode(), hashlib.sha256).hexdigest()


def notify(conn, owner, kind, title, body, stamp, resource=None, tx=None, dedupe=None):
    from .notification_preferences import allows
    if not allows(conn, owner, kind):
        return
    conn.execute('INSERT OR IGNORE INTO service_notifications VALUES (?,?,?,?,?,?,?,?,NULL,?)',
                 (uuid.uuid4().hex, owner, kind, title, body, resource, tx, stamp, dedupe))


def create(conn, user, kind, payload, recipient=None):
    stamp = security.timestamp()
    security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
    remaining = security.lock_remaining(conn, user.id, stamp)
    if remaining:
        raise security.locked(remaining)
    # Creation limit uses its own committed transaction at the router boundary.
    raw = secrets.token_urlsafe(32)
    challenge = digest(raw)
    # A code sent to another address proves that address (email change), so it stays an email code.
    factor = 'email' if recipient else transaction_factor(conn, user.id)
    if factor == 'setup_required':
        raise setup_required()
    code = f'{secrets.randbelow(1000000):06d}'
    conn.execute('''INSERT INTO action_challenges
        (id,owner_id,session_id,auth_version,kind,payload_json,otp_hash,created_at,expires_at)
        VALUES (?,?,?,?,?,?,?,?,?)''', (challenge, user.id, user.session_id, user.auth_version,
        kind, json.dumps(payload), {'totp': TOTP_MARK, 'pin': PIN_MARK}.get(factor) or otp_hash(challenge, code), stamp, stamp + 120))
    safe = {k: v for k, v in payload.items() if k not in ('password_hash',)}
    if factor in ('totp', 'pin'):
        return {'challenge_id': raw, 'kind': kind, 'summary': safe, 'expires_in': 120, 'method': factor,
                'delivery': 'authenticator' if factor == 'totp' else 'pin',
                'message': 'Enter the code from your authenticator app to confirm.' if factor == 'totp' else 'Enter your 6-digit transaction PIN to confirm.'}
    destination = recipient or conn.execute('SELECT email FROM users WHERE id=?', (user.id,)).fetchone()[0]
    conn.execute('''INSERT INTO dev_outbox
        (id,user_id,recipient,kind,created_at,expires_at,secret_text,challenge_id,body)
        VALUES (?,?,?,?,?,?,?,?,?)''', (uuid.uuid4().hex, user.id, destination, 'ACTION_' + kind,
        stamp, stamp + 120, code, challenge, 'Confirm only the action you requested in NovaBank.'))
    return {'challenge_id': raw, 'kind': kind, 'summary': safe, 'expires_in': 120, 'method': 'email',
            'delivery': 'local_demo_outbox', 'message': 'Enter the code from the local demo inbox to confirm.'}


def limit(db, user):
    with transaction(db) as conn:
        allowed = quota(conn, 'customer-action', user.id, 15, 900, security.timestamp())
    if not allowed:
        raise HTTPException(429, 'Too many confirmation requests. Try again later.')


def confirm(db, user, raw, code, key):
    from .customer_services import apply_profile_change
    from .products import execute
    if not key:
        raise HTTPException(400, 'An Idempotency-Key is required.')
    challenge = digest(raw)
    rejection = None
    result = None
    with transaction(db) as conn:
        stamp = security.timestamp()
        security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        row = conn.execute('SELECT * FROM action_challenges WHERE id=? AND owner_id=? AND session_id=?',
                           (challenge, user.id, user.session_id)).fetchone()
        if not row:
            raise HTTPException(404, 'Confirmation not found.')
        if row['consumed_at'] is not None:
            if row['idempotency_key'] != key:
                raise HTTPException(409, 'This confirmation has already been used.')
            return json.loads(row['response_json'])
        if conn.execute('SELECT 1 FROM action_challenges WHERE owner_id=? AND idempotency_key=?', (user.id, key)).fetchone():
            raise HTTPException(409, 'Idempotency key belongs to another action.')
        if row['auth_version'] != user.auth_version or row['expires_at'] <= stamp or row['attempts'] >= 5:
            raise HTTPException(400, 'Confirmation expired or exhausted. Request a new code.')
        remaining = security.lock_remaining(conn, user.id, stamp)
        if remaining:
            raise security.locked(remaining)
        # Email-change codes prove the new address, so they never accept the PIN or authenticator.
        check = None if row['otp_hash'] not in (TOTP_MARK, PIN_MARK) and row['kind'] in ('PROFILE_EMAIL', 'PROFILE_PHONE') else verify_factor(conn, db, user.id, code, stamp)
        if check == 'locked':
            raise HTTPException(423, 'Too many wrong PINs. Try again in 15 minutes.')
        valid = check == 'ok' if check else (row['otp_hash'] not in (TOTP_MARK, PIN_MARK) and hmac.compare_digest(row['otp_hash'], otp_hash(challenge, code)))
        if not valid:
            conn.execute('UPDATE action_challenges SET attempts=attempts+1 WHERE id=?', (challenge,))
            security.failure(conn, user.id, stamp)
            rejection = HTTPException(400, 'Incorrect verification code.')
        else:
            payload = json.loads(row['payload_json'])
            if row['kind'].startswith('PROFILE_'):
                result = apply_profile_change(conn, user, row['kind'], payload, stamp)
            else:
                result = execute(conn, user, row['kind'], payload, challenge, stamp)
            conn.execute('UPDATE action_challenges SET consumed_at=?,idempotency_key=?,response_json=?,payload_json=? WHERE id=?',
                         (stamp, key, json.dumps(result), '{}', challenge))
            conn.execute('UPDATE dev_outbox SET secret_text=NULL WHERE challenge_id=?', (challenge,))
            security.clear_failures(conn, user.id)
    if rejection:
        raise rejection
    return result
