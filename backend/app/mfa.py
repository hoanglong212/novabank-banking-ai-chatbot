"""Password-to-MFA login and purpose-bound email/TOTP challenge consumption."""
import hmac
import secrets
import uuid
from fastapi import HTTPException
from . import session_security as security, sessions
from .auth import DUMMY_HASH, verify_password
from .auth_crypto import otp_digest, decrypt_secret, match_totp
from .identity import transaction, digest, lookup_principal, quota, audit


def invalid():
    return HTTPException(400, 'The code is invalid, expired or already used. Request a new code or sign in again.')


def challenge_row(conn, raw, purpose, stamp, user=None):
    row = conn.execute('''SELECT c.* FROM mfa_challenges c JOIN users u ON u.id=c.user_id
        WHERE c.id=? AND c.purpose=? AND c.consumed_at IS NULL AND c.expires_at>? AND c.attempts<5
        AND c.auth_version=u.auth_version AND u.status='ACTIVE' ''', (digest(raw), purpose, stamp)).fetchone()
    if row is None or (user and (row['user_id'] != user.id or row['session_id'] != user.session_id)):
        raise invalid()
    return row


def send_code(conn, row, stamp):
    if row['sends'] >= 4:
        raise HTTPException(429, 'No more resends for this challenge. Please sign in again.')
    if row['sent_at'] is not None and row['sent_at'] + 30 > stamp:
        raise HTTPException(429, 'Please wait 30 seconds before requesting another code.', headers={'Retry-After': '30'})
    if not quota(conn, 'mfa-mail:' + row['purpose'], row['user_id'], 10, 3600, stamp):
        raise HTTPException(429, 'Too many verification messages. Please try again later.')
    code = str(secrets.randbelow(1_000_000)).zfill(6)
    # Avoid accidentally reissuing the same code on resend.
    while row['otp_hash'] and hmac.compare_digest(otp_digest(row['id'], code), row['otp_hash']):
        code = str(secrets.randbelow(1_000_000)).zfill(6)
    expiry = min(stamp + 120, row['expires_at'])
    security.scrub_challenge(conn, row['id'])
    conn.execute("UPDATE mfa_challenges SET method='email',otp_hash=?,otp_expires_at=?,sends=sends+1,sent_at=? WHERE id=?",
                 (otp_digest(row['id'], code), expiry, stamp, row['id']))
    kind = 'LOGIN_OTP' if row['purpose'] == 'LOGIN' else 'DISABLE_TOTP_OTP'
    conn.execute('''INSERT INTO dev_outbox (id,user_id,recipient,kind,created_at,expires_at,secret_text,challenge_id,body)
        SELECT ?,id,email,?,?,?,?,?,? FROM users WHERE id=?''',
        (uuid.uuid4().hex, kind, stamp, expiry, code, row['id'], 'Use this one-time code only for ' + row['purpose'].lower().replace('_', ' ') + '.', row['user_id']))


def create_challenge(conn, user, purpose, ip, ua, stamp, method='email', session_id=None):
    raw = secrets.token_urlsafe(32)
    conn.execute('''INSERT INTO mfa_challenges
        (id,user_id,auth_version,purpose,session_id,method,created_at,expires_at,ip,user_agent)
        VALUES (?,?,?,?,?,?,?,?,?,?)''', (digest(raw), user.id, user.auth_version, purpose, session_id, method, stamp, stamp + 300, ip, ua))
    row = conn.execute('SELECT * FROM mfa_challenges WHERE id=?', (digest(raw),)).fetchone()
    if method == 'email':
        send_code(conn, row, stamp)
    return {'mfa_required': True, 'challenge_id': raw, 'method': method, 'expires_in': 300,
            'message': 'Enter your authenticator code.' if method == 'totp' else 'A verification code is available in the local demo inbox.'}


def begin_login(db, username, password, ip, ua):
    key = username.strip().lower()
    candidate = lookup_principal(db, key)
    correct = verify_password(password, candidate.password_hash if candidate else DUMMY_HASH)
    rejection = None
    result = None
    with transaction(db) as conn:
        stamp = security.timestamp()
        current = conn.execute("SELECT id,password_hash FROM users WHERE id=? AND status='ACTIVE'", (key,)).fetchone()
        remaining = security.lock_remaining(conn, key, stamp)
        if remaining:
            security.history(conn, current['id'] if current else None, 'LOCKED', 'password', ip, ua, stamp)
            rejection = security.locked(remaining)
        elif not correct or candidate is None or current is None or current['password_hash'] != candidate.password_hash:
            security.failure(conn, key, stamp)
            security.history(conn, current['id'] if current else None, 'PASSWORD_FAILED', 'password', ip, ua, stamp)
            rejection = HTTPException(401, 'Invalid username or password')
        else:
            configured = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (key,)).fetchone()
            result = create_challenge(conn, candidate, 'LOGIN', ip, ua, stamp, 'totp' if configured and configured[0] else 'email')
    if rejection:
        raise rejection
    return result


def resend(db, raw):
    with transaction(db) as conn:
        stamp = security.timestamp()
        row = challenge_row(conn, raw, 'LOGIN', stamp)
        remaining = security.lock_remaining(conn, row['user_id'], stamp)
        if remaining:
            raise security.locked(remaining)
        send_code(conn, row, stamp)
    return {'method': 'email', 'message': 'A new code is available in the local demo inbox.'}


def complete(db, raw, code, purpose='LOGIN', user=None):
    rejection = None
    result = None
    with transaction(db) as conn:
        stamp = security.timestamp()
        if user:
            security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        row = challenge_row(conn, raw, purpose, stamp, user)
        remaining = security.lock_remaining(conn, row['user_id'], stamp)
        step = None
        if remaining:
            rejection = security.locked(remaining)
        elif row['method'] == 'email':
            accepted = row['otp_expires_at'] > stamp and hmac.compare_digest(otp_digest(row['id'], code), row['otp_hash'])
        else:
            settings = conn.execute('SELECT * FROM mfa_settings WHERE user_id=?', (row['user_id'],)).fetchone()
            if settings and settings['secret_encrypted']:
                step = match_totp(decrypt_secret(db, settings['secret_encrypted']), code, stamp, settings['last_step'])
            accepted = step is not None
        if rejection is None and not accepted:
            conn.execute('UPDATE mfa_challenges SET attempts=attempts+1 WHERE id=?', (row['id'],))
            security.failure(conn, row['user_id'], stamp)
            security.history(conn, row['user_id'], 'MFA_FAILED', row['method'], row['ip'], row['user_agent'], stamp)
            if row['attempts'] + 1 >= 5:
                security.consume_challenge(conn, row['id'], stamp)
            rejection = invalid()
        elif rejection is None:
            if step is not None:
                conn.execute('UPDATE mfa_settings SET last_step=? WHERE user_id=?', (step, row['user_id']))
            security.consume_challenge(conn, row['id'], stamp)
            security.clear_failures(conn, row['user_id'])
            if purpose == 'LOGIN':
                principal = lookup_principal(db, row['user_id'])
                result = sessions.create(conn, principal, row['ip'], row['user_agent'], row['method'], stamp)
            else:
                conn.execute('DELETE FROM mfa_settings WHERE user_id=?', (user.id,))
                security.revoke_user(conn, user.id, stamp, 'MFA_CHANGED', except_session=user.session_id)
                audit(conn, user.id, 'TOTP_DISABLED', stamp)
                result = {'message': 'Authenticator disabled. Email verification remains required. Other sessions have ended.'}
    if rejection:
        raise rejection
    return result
