"""Server-owned sessions and atomic opaque refresh-token rotation."""
from contextlib import closing
import secrets
import uuid
from dataclasses import replace
from fastapi import HTTPException
from . import session_security as security
from .identity import transaction, digest, lookup_principal, audit
from .auth import issue_token, TTL_SECONDS


def response(user, row, refresh_token):
    principal = replace(user, session_id=row['id'])
    return {'access_token': issue_token(principal), 'refresh_token': refresh_token, 'token_type': 'bearer',
            'expires_in': TTL_SECONDS, 'session_id': row['id'], 'idle_expires_at': row['last_active_at'] + security.IDLE_SECONDS,
            'absolute_expires_at': row['absolute_expires_at'],
            'user': {'id': user.id, 'name': user.name, 'role': user.role, 'permissions': sorted(user.permissions)}}


def mint_refresh(conn, session_id, stamp):
    raw = secrets.token_urlsafe(32)
    conn.execute('INSERT INTO refresh_tokens VALUES (?,?,?,NULL)', (digest(raw), session_id, stamp))
    return raw


def create(conn, user, ip, ua, method, stamp):
    session_id = uuid.uuid4().hex
    seen = conn.execute("SELECT 1 FROM login_attempts WHERE user_id=? AND result='SUCCESS' AND ip=? AND user_agent=?", (user.id, ip, ua)).fetchone()
    previous = conn.execute("SELECT 1 FROM login_attempts WHERE user_id=? AND result='SUCCESS'", (user.id,)).fetchone()
    conn.execute('INSERT INTO user_sessions VALUES (?,?,?,?,?,?,NULL,NULL,?,?,?)',
                 (session_id, user.id, user.auth_version, stamp, stamp, stamp + security.ABSOLUTE_SECONDS, ip, ua, method))
    security.history(conn, user.id, 'SUCCESS', method, ip, ua, stamp)
    if previous and not seen:
        conn.execute('''INSERT INTO dev_outbox (id,user_id,recipient,kind,created_at,body)
            SELECT ?,id,email,'NEW_DEVICE',?,? FROM users WHERE id=?''',
            (uuid.uuid4().hex, stamp, f'A new sign-in was detected. Device: {ua}. IP: {ip}. Review your sessions in Profile.', user.id))
    audit(conn, user.id, 'SESSION_CREATED', stamp)
    row = conn.execute('SELECT * FROM user_sessions WHERE id=?', (session_id,)).fetchone()
    return response(user, row, mint_refresh(conn, session_id, stamp))


def rotate(db, raw):
    rejection = None
    result = None
    with transaction(db) as conn:
        stamp = security.timestamp()
        token = conn.execute('SELECT * FROM refresh_tokens WHERE token_hash=?', (digest(raw),)).fetchone()
        if token is None:
            rejection = HTTPException(401, 'Invalid refresh token. Please sign in again.')
        else:
            row = conn.execute('SELECT * FROM user_sessions WHERE id=?', (token['session_id'],)).fetchone()
            if token['used_at'] is not None:
                security.revoke(conn, row['id'], stamp, 'REFRESH_REUSE')
                rejection = HTTPException(401, 'Refresh token reused. Please sign in again.')
            else:
                try:
                    security.active_session(conn, row['id'], row['user_id'], row['auth_version'], stamp)
                except HTTPException as exc:
                    rejection = exc
                if rejection is None:
                    user = lookup_principal(db, row['user_id'])
                    conn.execute('UPDATE refresh_tokens SET used_at=? WHERE token_hash=?', (stamp, digest(raw)))
                    result = response(user, row, mint_refresh(conn, row['id'], stamp))
    # Reuse revocation must commit before returning an error.
    if rejection:
        raise rejection
    return result


def list_sessions(db, user):
    stamp = security.timestamp()
    with closing(db.connect()) as conn:
        rows = conn.execute('''SELECT id,created_at,last_active_at,absolute_expires_at,ip,user_agent,method FROM user_sessions
            WHERE user_id=? AND revoked_at IS NULL AND auth_version=? AND last_active_at+?>? AND absolute_expires_at>?
            ORDER BY created_at DESC,id DESC LIMIT 100''', (user.id, user.auth_version, security.IDLE_SECONDS, stamp, stamp)).fetchall()
    return {'items': [{**dict(row), 'current': row['id'] == user.session_id} for row in rows]}


def revoke_owned(db, user, session_id):
    with transaction(db) as conn:
        if conn.execute('SELECT 1 FROM user_sessions WHERE id=? AND user_id=?', (session_id, user.id)).fetchone() is None:
            raise HTTPException(404, 'Session not found')
        security.revoke(conn, session_id, security.timestamp(), 'SIGNED_OUT')
    return {'message': 'Session signed out.'}


def activity(db, user):
    with transaction(db) as conn:
        stamp = security.timestamp()
        security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
        conn.execute('UPDATE user_sessions SET last_active_at=? WHERE id=?', (stamp, user.session_id))
    return {'idle_expires_at': stamp + security.IDLE_SECONDS}


def login_history(db, user, limit, offset):
    with closing(db.connect()) as conn:
        total = conn.execute('SELECT COUNT(*) FROM login_attempts WHERE user_id=?', (user.id,)).fetchone()[0]
        rows = conn.execute('SELECT * FROM login_attempts WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT ? OFFSET ?', (user.id, limit, offset)).fetchall()
    return {'items': [dict(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset}
