from contextlib import closing
from urllib.parse import quote, urlencode
from fastapi import HTTPException
from . import mfa, session_security as security
from .auth import verify_password
from .auth_crypto import new_totp_secret, encrypt_secret, decrypt_secret, match_totp
from .identity import transaction, audit


# Marks stored instead of an emailed-code hash: the code comes from the customer, not from us.
TOTP_MARK = 'TOTP'
PIN_MARK = 'PIN'
PIN_MAX_FAILURES = 5
PIN_LOCK_SECONDS = 900


def transaction_factor(conn, user_id):
    """'totp' (authenticator) > 'pin' (customer-chosen) > 'setup_required' (new account) > 'email' (API fallback)."""
    row = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (user_id,)).fetchone()
    if row and row[0]:
        return 'totp'
    if conn.execute('SELECT 1 FROM transaction_pins WHERE user_id=?', (user_id,)).fetchone():
        return 'pin'
    return 'setup_required' if conn.execute('SELECT 1 FROM totp_required WHERE user_id=?', (user_id,)).fetchone() else 'email'


def verify_totp(conn, db, user_id, code, stamp):
    """Check an authenticator code and burn its time step, so a code works once across sign-in and transactions."""
    row = conn.execute('SELECT secret_encrypted,last_step FROM mfa_settings WHERE user_id=?', (user_id,)).fetchone()
    if not row or not row[0]:
        return False
    step = match_totp(decrypt_secret(db, row[0]), code, int(stamp), row[1] if row[1] is not None else -1)
    if step is None:
        return False
    conn.execute('UPDATE mfa_settings SET last_step=? WHERE user_id=?', (step, user_id))
    return True


def verify_pin(conn, user_id, pin, stamp):
    """'ok', 'bad' or 'locked'. A static PIN can be guessed, so five misses lock it for 15 minutes."""
    row = conn.execute('SELECT * FROM transaction_pins WHERE user_id=?', (user_id,)).fetchone()
    if not row:
        return 'bad'
    if row['locked_until'] > stamp:
        return 'locked'
    if verify_password(pin, row['pin_hash']):
        conn.execute('UPDATE transaction_pins SET failures=0 WHERE user_id=?', (user_id,))
        return 'ok'
    failures = row['failures'] + 1
    locked = failures >= PIN_MAX_FAILURES
    conn.execute('UPDATE transaction_pins SET failures=?,locked_until=? WHERE user_id=?',
                 (0 if locked else failures, stamp + PIN_LOCK_SECONDS if locked else 0, user_id))
    audit(conn, user_id, 'PIN_LOCKED' if locked else 'PIN_REJECTED', int(stamp))
    return 'locked' if locked else 'bad'


def verify_factor(conn, db, user_id, code, stamp):
    """Live check against whatever the customer uses now: None means use the emailed code instead."""
    factor = transaction_factor(conn, user_id)
    if factor == 'totp':
        return 'ok' if verify_totp(conn, db, user_id, code, stamp) else 'bad'
    if factor == 'pin':
        return verify_pin(conn, user_id, code, int(stamp))
    return None


def setup_required():
    return HTTPException(403, 'Set your 6-digit transaction PIN before making transactions.')


def weak_pin(pin):
    return len(set(pin)) == 1 or pin in '0123456789' or pin in '9876543210'


def set_pin(db, user, password, pin):
    if user.role and user.role != 'customer':
        raise HTTPException(403, 'Only customers have a transaction PIN.')
    if weak_pin(pin):
        raise HTTPException(422, 'Choose a PIN that is not repeated or sequential digits.')
    check_password(db, user, password)
    from .identity import hash_password
    hashed = hash_password(pin)
    with transaction(db) as conn:
        stamp = security.timestamp()
        security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        conn.execute('''INSERT INTO transaction_pins (user_id,pin_hash,failures,locked_until,updated_at) VALUES (?,?,0,0,?)
            ON CONFLICT(user_id) DO UPDATE SET pin_hash=excluded.pin_hash,failures=0,locked_until=0,updated_at=excluded.updated_at''',
            (user.id, hashed, stamp))
        audit(conn, user.id, 'PIN_SET', stamp)
    return {'message': 'Transaction PIN saved.'}


def status(db, user):
    with closing(db.connect()) as conn:
        row = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (user.id,)).fetchone()
        pin = bool(conn.execute('SELECT 1 FROM transaction_pins WHERE user_id=?', (user.id,)).fetchone())
        required = bool(conn.execute('SELECT 1 FROM totp_required WHERE user_id=?', (user.id,)).fetchone())
    totp = bool(row and row[0])
    return {'totp_enabled': totp, 'email_fallback': True, 'pin_set': pin, 'setup_required': required and not pin and not totp}


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
    from base64 import b64encode
    from .local_qr import png
    qr = 'data:image/png;base64,' + b64encode(png(uri)).decode()
    return {'secret': secret, 'otpauth_uri': uri, 'qr_png': qr, 'expires_in': 300}


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
