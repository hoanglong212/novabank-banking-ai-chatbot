"""Shared persisted security controls. Call mutations inside identity.transaction."""
import time
import unicodedata
import uuid
from fastapi import HTTPException
from .identity import digest, audit

IDLE_SECONDS = 300
ABSOLUTE_SECONDS = 8 * 60 * 60
LOCK_SECONDS = 900


def timestamp():
    return int(time.time())


def clean(value, limit):
    return ''.join(c for c in value[:limit] if not unicodedata.category(c).startswith('C'))


def metadata(request):
    return (clean(request.client.host if request.client else 'unknown', 64), clean(request.headers.get('user-agent', 'Unknown device'), 300))


def history(conn, user_id, result, method, ip, ua, stamp):
    conn.execute('INSERT INTO login_attempts VALUES (?,?,?,?,?,?,?)', (uuid.uuid4().hex, user_id, stamp, result, method, ip, ua))


def lock_remaining(conn, username, stamp):
    row = conn.execute('SELECT locked_until FROM login_lockouts WHERE subject_hash=?', (digest(username),)).fetchone()
    return max(0, row[0] - stamp) if row else 0


def failure(conn, username, stamp):
    key = digest(username)
    row = conn.execute('SELECT * FROM login_lockouts WHERE subject_hash=?', (key,)).fetchone()
    count = row['failures'] + 1 if row and row['window_start'] + LOCK_SECONDS > stamp and row['locked_until'] <= stamp else 1
    start = row['window_start'] if row and count > 1 else stamp
    until = stamp + LOCK_SECONDS if count >= 5 else 0
    conn.execute('INSERT INTO login_lockouts VALUES (?,?,?,?) ON CONFLICT(subject_hash) DO UPDATE SET failures=excluded.failures,window_start=excluded.window_start,locked_until=excluded.locked_until', (key, count, start, until))


def clear_failures(conn, user_id):
    conn.execute('DELETE FROM login_lockouts WHERE subject_hash=?', (digest(user_id),))


def locked(seconds):
    return HTTPException(429, 'Too many failed attempts. Try again in 15 minutes.', headers={'Retry-After': str(seconds)})


def scrub_challenge(conn, challenge_hash):
    conn.execute('UPDATE dev_outbox SET secret_text=NULL WHERE challenge_id=?', (challenge_hash,))


def consume_challenge(conn, challenge_hash, stamp):
    conn.execute('UPDATE mfa_challenges SET consumed_at=? WHERE id=?', (stamp, challenge_hash))
    scrub_challenge(conn, challenge_hash)


def revoke(conn, session_id, stamp, reason):
    row = conn.execute('SELECT user_id FROM user_sessions WHERE id=? AND revoked_at IS NULL', (session_id,)).fetchone()
    if row:
        conn.execute('UPDATE user_sessions SET revoked_at=?,revoke_reason=? WHERE id=?', (stamp, reason, session_id))
        audit(conn, row['user_id'], 'SESSION_' + reason, stamp)


def revoke_user(conn, user_id, stamp, reason, except_session=None):
    rows = conn.execute('SELECT id FROM user_sessions WHERE user_id=? AND revoked_at IS NULL AND (? IS NULL OR id!=?)',
                        (user_id, except_session, except_session)).fetchall()
    for row in rows:
        revoke(conn, row[0], stamp, reason)
    for row in conn.execute('SELECT id FROM mfa_challenges WHERE user_id=? AND consumed_at IS NULL', (user_id,)).fetchall():
        consume_challenge(conn, row[0], stamp)


def active_session(conn, session_id, user_id, version, stamp):
    row = conn.execute('''SELECT s.* FROM user_sessions s JOIN users u ON u.id=s.user_id
        WHERE s.id=? AND s.user_id=? AND s.auth_version=? AND u.auth_version=s.auth_version AND u.status='ACTIVE'
        AND s.revoked_at IS NULL AND s.last_active_at+?>? AND s.absolute_expires_at>?''',
        (session_id, user_id, version, IDLE_SECONDS, stamp, stamp)).fetchone()
    if row is None:
        raise HTTPException(401, 'Session expired or revoked. Please sign in again.')
    return row
