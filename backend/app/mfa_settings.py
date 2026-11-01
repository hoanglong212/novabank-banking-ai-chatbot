from contextlib import closing
from urllib.parse import quote, urlencode
from fastapi import HTTPException
from . import mfa, session_security as security
from .auth import verify_password
from .auth_crypto import new_totp_secret, encrypt_secret, decrypt_secret, match_totp
from .identity import transaction, audit


def status(db, user):
    with closing(db.connect()) as conn:
        row = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (user.id,)).fetchone()
    return {'totp_enabled': bool(row and row[0]), 'email_fallback': True}


def check_password(db, user, password):
    rejection = None
    with transaction(db) as conn:
        stamp = security.timestamp()
        row = security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        remaining = security.lock_remaining(conn, user.id, stamp)
        if remaining:
            rejection = security.locked(remaining)
        elif not verify_password(password, user.password_hash):
            security.failure(conn, user.id, stamp)
            security.history(conn, user.id, 'PASSWORD_FAILED', 'security-settings', row['ip'], row['user_agent'], stamp)
            rejection = HTTPException(400, 'Password is incorrect.')
    if rejection:
        raise rejection


def setup(db, user, password):
    check_password(db, user, password)
    with transaction(db) as conn:
        stamp = security.timestamp()
        security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        row = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (user.id,)).fetchone()
        if row and row[0]:
            raise HTTPException(409, 'Authenticator is already enabled. Disable it before replacing it.')
        secret = new_totp_secret()
        encrypted = encrypt_secret(db, secret)
        conn.execute('''INSERT INTO mfa_settings (user_id,pending_secret,pending_expires_at,pending_session_id)
            VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET pending_secret=excluded.pending_secret,
            pending_expires_at=excluded.pending_expires_at,pending_session_id=excluded.pending_session_id,pending_attempts=0''',
            (user.id, encrypted, stamp + 300, user.session_id))
    uri = 'otpauth://totp/' + quote('NovaBank:' + user.id, safe='') + '?' + urlencode({'secret': secret, 'issuer': 'NovaBank', 'algorithm': 'SHA1', 'digits': 6, 'period': 30})
    return {'secret': secret, 'otpauth_uri': uri, 'expires_in': 300}


def enable(db, user, code):
    rejection = None
    with transaction(db) as conn:
        stamp = security.timestamp()
        security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        row = conn.execute('SELECT * FROM mfa_settings WHERE user_id=?', (user.id,)).fetchone()
        if not row or row['secret_encrypted'] or not row['pending_secret'] or row['pending_session_id'] != user.session_id or row['pending_expires_at'] <= stamp or row['pending_attempts'] >= 5:
            raise mfa.invalid()
        remaining = security.lock_remaining(conn, user.id, stamp)
        if remaining:
            raise security.locked(remaining)
        step = match_totp(decrypt_secret(db, row['pending_secret']), code, stamp)
        if step is None:
            conn.execute('UPDATE mfa_settings SET pending_attempts=pending_attempts+1 WHERE user_id=?', (user.id,))
            security.failure(conn, user.id, stamp)
            rejection = mfa.invalid()
        else:
            conn.execute('''UPDATE mfa_settings SET secret_encrypted=pending_secret,last_step=?,pending_secret=NULL,
                pending_expires_at=NULL,pending_session_id=NULL,pending_attempts=0 WHERE user_id=?''', (step, user.id))
            security.revoke_user(conn, user.id, stamp, 'MFA_CHANGED', except_session=user.session_id)
            security.clear_failures(conn, user.id)
            audit(conn, user.id, 'TOTP_ENABLED', stamp)
    if rejection:
        raise rejection
    return {'message': 'Authenticator enabled. Other sessions have ended.'}


def disable_request(db, user, password):
    check_password(db, user, password)
    with transaction(db) as conn:
        stamp = security.timestamp()
        row = security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        settings = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (user.id,)).fetchone()
        if not settings or not settings[0]:
            raise HTTPException(409, 'Authenticator is not enabled.')
        for previous in conn.execute("SELECT id FROM mfa_challenges WHERE user_id=? AND purpose='DISABLE_TOTP' AND consumed_at IS NULL", (user.id,)).fetchall():
            security.consume_challenge(conn, previous[0], stamp)
        return mfa.create_challenge(conn, user, 'DISABLE_TOTP', row['ip'], row['user_agent'], stamp, session_id=user.session_id)
