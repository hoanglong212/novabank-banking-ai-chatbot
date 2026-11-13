"""Account lifecycle. Tokens and financial mutations never leave the transaction."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import secrets
import sqlite3
import time
import uuid
from fastapi import HTTPException
from .auth import DemoPrincipal

VERIFY_TTL = 24 * 60 * 60
RESET_TTL = 15 * 60
ACCEPTED = {'message': 'If the details are eligible, instructions are available in the local demo inbox.'}


def timestamp():
    return int(time.time())


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()
    return f'pbkdf2_sha256$600000${salt}${hashed}'


@contextmanager
def transaction(db):
    try:
        with closing(db.connect()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            yield conn
    except sqlite3.Error as exc:
        raise HTTPException(503, 'Account service is temporarily unavailable. Please retry.') from exc


def lookup_principal(db, user_id):
    try:
        with closing(db.connect()) as conn:
            row = conn.execute("SELECT * FROM users WHERE id=? AND status='ACTIVE'", (user_id,)).fetchone()
            if row is None:
                return None
            accounts = tuple(r[0] for r in conn.execute('SELECT id FROM accounts WHERE owner_id=? ORDER BY id', (user_id,)))
            return DemoPrincipal(row['id'], row['name'], row['password_hash'], accounts, row['role'], row['auth_version'])
    except sqlite3.Error as exc:
        raise HTTPException(503, 'Account service is temporarily unavailable. Please retry.') from exc


def quota(conn, scope, subject, limit, window, stamp):
    # A fixed-window persistent counter; caller owns the surrounding transaction.
    start = stamp - stamp % window
    key = digest(subject)
    conn.execute('DELETE FROM identity_limits WHERE starts_at<?', (stamp - 7200,))
    conn.execute('''INSERT INTO identity_limits VALUES (?,?,?,1)
                    ON CONFLICT(scope,subject_hash,starts_at) DO UPDATE SET attempts=attempts+1''', (scope, key, start))
    count = conn.execute('SELECT attempts FROM identity_limits WHERE scope=? AND subject_hash=? AND starts_at=?',
                         (scope, key, start)).fetchone()[0]
    return count <= limit


def request_limit(db, action, peer):
    with transaction(db) as conn:
        allowed = quota(conn, 'request:' + action, peer, 20, 900, timestamp())
    if not allowed:
        raise HTTPException(429, 'Too many requests. Please try again in 15 minutes.', headers={'Retry-After': '900'})


def audit(conn, user_id, action, stamp):
    conn.execute('INSERT INTO identity_audit VALUES (?,?,?,?)', (uuid.uuid4().hex, user_id, action, stamp))


def invalidate(conn, user_id, purpose, stamp):
    conn.execute('UPDATE identity_tokens SET consumed_at=? WHERE user_id=? AND purpose=? AND consumed_at IS NULL',
                 (stamp, user_id, purpose))
    conn.execute('UPDATE dev_outbox SET action_path=NULL WHERE user_id=? AND kind=?', (user_id, purpose))


def deliver(conn, user, purpose, stamp):
    invalidate(conn, user['id'], purpose, stamp)
    raw = secrets.token_urlsafe(32)
    expiry = stamp + (VERIFY_TTL if purpose == 'VERIFY_EMAIL' else RESET_TTL)
    route = 'verify-email' if purpose == 'VERIFY_EMAIL' else 'reset-password'
    conn.execute('INSERT INTO identity_tokens VALUES (?,?,?,?,NULL)', (digest(raw), user['id'], purpose, expiry))
    conn.execute('INSERT INTO dev_outbox (id,user_id,recipient,kind,created_at,expires_at,action_path) VALUES (?,?,?,?,?,?,?)',
                 (uuid.uuid4().hex, user['id'], user['email'], purpose, stamp, expiry, f'/#{route}?token={raw}'))


def register(db, data):
    # Hash even for duplicates, outside the write transaction to keep lock duration short.
    hashed = hash_password(data.password)
    stamp = timestamp()
    with transaction(db) as conn:
        eligible = quota(conn, 'delivery:VERIFY_EMAIL', data.email, 5, 3600, stamp)
        if conn.execute('SELECT 1 FROM users WHERE id=? OR email=?', (data.username, data.email)).fetchone():
            return ACCEPTED
        conn.execute('INSERT INTO users VALUES (?,?,?,?,?,?,0,?)',
                     (data.username, data.name, data.email, hashed, 'customer', 'PENDING',
                      datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec='seconds')))
        conn.execute('INSERT OR IGNORE INTO totp_required VALUES (?)', (data.username,))
        if eligible:
            deliver(conn, {'id': data.username, 'email': data.email}, 'VERIFY_EMAIL', stamp)
        audit(conn, data.username, 'REGISTERED', stamp)
    return ACCEPTED


def send_instructions(db, email, purpose):
    stamp = timestamp()
    expected_status = 'PENDING' if purpose == 'VERIFY_EMAIL' else 'ACTIVE'
    with transaction(db) as conn:
        eligible = quota(conn, 'delivery:' + purpose, email, 5, 3600, stamp)
        row = conn.execute('SELECT id,email FROM users WHERE email=? AND status=?', (email, expected_status)).fetchone()
        if eligible and row:
            deliver(conn, row, purpose, stamp)
            audit(conn, row['id'], purpose + '_REQUESTED', stamp)
    return ACCEPTED


def valid_token(conn, raw, purpose, stamp):
    row = conn.execute('''SELECT t.user_id FROM identity_tokens t JOIN users u ON u.id=t.user_id
        WHERE t.token_hash=? AND t.purpose=? AND t.consumed_at IS NULL AND t.expires_at>?
        AND u.status=?''', (digest(raw), purpose, stamp, 'PENDING' if purpose == 'VERIFY_EMAIL' else 'ACTIVE')).fetchone()
    if row is None:
        raise HTTPException(400, 'This link is invalid or expired. Request a new link.')
    return row['user_id']


def verify_email(db, raw):
    with transaction(db) as conn:
        stamp = timestamp()  # Check expiry after acquiring the write lock, not before a possible wait.
        user_id = valid_token(conn, raw, 'VERIFY_EMAIL', stamp)
        name = conn.execute('SELECT name FROM users WHERE id=?', (user_id,)).fetchone()[0]
        account_id = 'ACC-' + uuid.uuid4().hex[:20].upper()
        conn.execute("INSERT INTO accounts VALUES (?,?,?,0,'ACTIVE')", (account_id, user_id, name))
        conn.execute("INSERT INTO ledger_accounts VALUES (?,?,'CUSTOMER')", (account_id, account_id))
        conn.execute("UPDATE users SET status='ACTIVE' WHERE id=?", (user_id,))
        invalidate(conn, user_id, 'VERIFY_EMAIL', stamp)
        audit(conn, user_id, 'EMAIL_VERIFIED', stamp)
    return {'message': 'Email verified. Your demo account is ready. Please sign in.'}


def reset_password(db, raw, password):
    hashed = hash_password(password)
    with transaction(db) as conn:
        stamp = timestamp()
        user_id = valid_token(conn, raw, 'RESET_PASSWORD', stamp)
        conn.execute('UPDATE users SET password_hash=?,auth_version=auth_version+1 WHERE id=?', (hashed, user_id))
        invalidate(conn, user_id, 'RESET_PASSWORD', stamp)
        from .session_security import revoke_user, clear_failures
        revoke_user(conn, user_id, stamp, 'PASSWORD_RESET')
        clear_failures(conn, user_id)
        email = conn.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()[0]
        conn.execute('INSERT INTO dev_outbox (id,user_id,recipient,kind,created_at,expires_at,action_path) VALUES (?,?,?,?,?,NULL,NULL)',
                     (uuid.uuid4().hex, user_id, email, 'PASSWORD_CHANGED', stamp))
        audit(conn, user_id, 'PASSWORD_RESET', stamp)
    return {'message': 'Password updated. Previous sessions have ended. Please sign in again.'}
