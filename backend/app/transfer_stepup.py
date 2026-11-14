"""Genuine TOTP step-up for new payees, bound to a frozen bank draft/session.

This is independent of final transaction confirmation. Successful new-payee
step-up requires a separately issued email OTP; known payees retain the existing
TOTP/PIN choice. A newly saved beneficiary is not proof of an earlier payment.
"""
import hashlib
import json
from datetime import datetime
from . import mfa_settings, session_security as security, transfers
from .identity import transaction, audit
from .posting import TransferError
from .database import now

PROOF_SECONDS = 120


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=18').fetchone():
        return
    conn.execute('''CREATE TABLE transfer_stepups (
        transfer_id TEXT NOT NULL REFERENCES transfers(id) ON DELETE CASCADE,
        session_id TEXT NOT NULL REFERENCES user_sessions(id),
        user_id TEXT NOT NULL REFERENCES users(id), auth_version INTEGER NOT NULL,
        fingerprint TEXT NOT NULL, factor_hash TEXT NOT NULL,
        verified_at INTEGER, expires_at INTEGER NOT NULL DEFAULT 0,
        attempts INTEGER NOT NULL DEFAULT 0, attempt_window_start INTEGER NOT NULL,
        PRIMARY KEY(transfer_id,session_id))''')
    conn.execute('''CREATE TABLE verified_payees (
        owner_id TEXT NOT NULL REFERENCES users(id),to_bank TEXT NOT NULL,to_account TEXT NOT NULL,
        verified_at TEXT NOT NULL,source_transfer_id TEXT REFERENCES transfers(id),
        origin TEXT NOT NULL CHECK(origin IN ('settled_transfer','migration','fixture_known')),
        CHECK(origin='fixture_known' OR source_transfer_id IS NOT NULL),
        PRIMARY KEY(owner_id,to_bank,to_account))''')
    conn.execute('''INSERT INTO verified_payees
        (owner_id,to_bank,to_account,verified_at,source_transfer_id,origin)
        SELECT owner_id,lower(to_bank),to_account,verified_at,id,'migration' FROM (
            SELECT t.*,COALESCE(t.completed_at,t.created_at) AS verified_at,
                ROW_NUMBER() OVER (PARTITION BY t.owner_id,lower(t.to_bank),t.to_account
                    ORDER BY COALESCE(t.completed_at,t.created_at) DESC,t.id DESC) AS ordinal
            FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
            WHERE t.status='COMPLETED' AND (t.internal=1 OR s.status='COMPLETED')
        ) WHERE ordinal=1''')
    conn.execute('INSERT INTO schema_migrations VALUES (18,?)', (stamp,))


def fingerprint(transfer):
    fields = ('id', 'owner_id', 'from_account', 'to_bank', 'to_account', 'to_name', 'amount_vnd', 'fee_vnd')
    return hashlib.sha256(json.dumps({k: transfer.get(k, 0 if k == 'fee_vnd' else None) for k in fields},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def new_recipient(conn, transfer):
    if conn.execute('SELECT 1 FROM verified_payees WHERE owner_id=? AND to_bank=lower(?) AND to_account=?',
            (transfer['owner_id'], transfer['to_bank'], transfer['to_account'])).fetchone():
        return False
    row = conn.execute('''SELECT 1 FROM transfers t
        LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
        WHERE t.owner_id=? AND lower(t.to_bank)=lower(?) AND t.to_account=? AND t.status='COMPLETED'
        AND (t.internal=1 OR s.status='COMPLETED') LIMIT 1''',
        (transfer['owner_id'], transfer['to_bank'], transfer['to_account'])).fetchone()
    return row is None


def remember_completed(conn, transfer_id):
    """Bank posting/settlement hook; no client-callable route grants payee trust."""
    row = conn.execute('''SELECT t.* FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
        WHERE t.id=? AND t.status='COMPLETED' AND (t.internal=1 OR s.status='COMPLETED')''', (transfer_id,)).fetchone()
    if not row:
        return False
    conn.execute('''INSERT INTO verified_payees VALUES (?,lower(?),?,?,?,'settled_transfer')
        ON CONFLICT(owner_id,to_bank,to_account) DO UPDATE SET verified_at=excluded.verified_at,
        source_transfer_id=excluded.source_transfer_id,origin=excluded.origin''',
        (row['owner_id'], row['to_bank'], row['to_account'], row['completed_at'] or now(), transfer_id))
    return True


def _factor(conn, user_id):
    row = conn.execute('SELECT secret_encrypted FROM mfa_settings WHERE user_id=?', (user_id,)).fetchone()
    encrypted = row[0] if row else None
    return hashlib.sha256(encrypted.encode()).hexdigest() if encrypted else ''


def status(conn, user, transfer):
    stamp = security.timestamp()
    security.active_session(conn, user.session_id, user.id, user.auth_version, stamp)
    if transfer.get('owner_id') != user.id:
        raise TransferError('TRANSFER_NOT_FOUND')
    required = transfer['status'] == 'PENDING_OTP' and new_recipient(conn, transfer)
    factor_hash = _factor(conn, user.id)
    proof = conn.execute('SELECT * FROM transfer_stepups WHERE transfer_id=? AND session_id=?', (transfer['id'], user.session_id)).fetchone()
    verified = bool(required and factor_hash and proof and proof['user_id'] == user.id
        and proof['auth_version'] == user.auth_version and proof['fingerprint'] == fingerprint(transfer)
        and proof['factor_hash'] == factor_hash and proof['verified_at'] is not None and proof['expires_at'] > stamp)
    return {'required': required, 'new_recipient': required, 'totp_enabled': bool(factor_hash),
        'enrollment_required': required and not factor_hash, 'verified': verified,
        'expires_in': max(0, proof['expires_at'] - stamp) if verified else 0,
        'confirmation_method': 'email' if verified else None,
        'message': 'Authenticator verification complete. Request a separate email code for this transfer.' if verified else
            'Set up an authenticator before paying this new recipient.' if required and not factor_hash else
            'Verify this exact transfer with a fresh authenticator code.' if required else 'No additional recipient verification is needed.'}


def require_stepup(conn, user, transfer):
    state = status(conn, user, transfer)
    if not state['required']:
        return
    if state['enrollment_required']:
        raise TransferError('AUTHENTICATOR_ENROLLMENT_REQUIRED')
    if not state['verified']:
        raise TransferError('STEP_UP_REQUIRED')
    remaining = security.lock_remaining(conn, user.id, security.timestamp())
    if remaining:
        raise security.locked(remaining)


def email_confirmation_required(conn, user, transfer):
    state = status(conn, user, transfer)
    return state['required'] and state['verified']


def describe(db, user, transfer_id):
    with db.connect() as conn:
        return status(conn, user, transfers._own_transfer(conn, transfer_id, user))


def verify(db, user, transfer_id, code):
    rejection = None
    with transaction(db) as conn:
        transfer = transfers._own_transfer(conn, transfer_id, user)
        state = status(conn, user, transfer)
        stamp = security.timestamp()
        if not state['required']:
            return state
        if datetime.fromisoformat(transfers._expires_at(transfer)).timestamp() <= stamp:
            raise TransferError('DRAFT_EXPIRED')
        if state['enrollment_required']:
            raise TransferError('AUTHENTICATOR_ENROLLMENT_REQUIRED')
        remaining = security.lock_remaining(conn, user.id, stamp)
        if remaining:
            raise security.locked(remaining)
        row = conn.execute('SELECT * FROM transfer_stepups WHERE transfer_id=? AND session_id=?', (transfer_id, user.session_id)).fetchone()
        attempts = row['attempts'] if row and row['attempt_window_start'] + 300 > stamp else 0
        window = row['attempt_window_start'] if attempts else stamp
        conn.execute('''INSERT INTO transfer_stepups
            (transfer_id,session_id,user_id,auth_version,fingerprint,factor_hash,attempt_window_start)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(transfer_id,session_id) DO NOTHING''',
            (transfer_id, user.session_id, user.id, user.auth_version, fingerprint(transfer), _factor(conn, user.id), window))
        if attempts >= 5:
            raise security.locked(300)
        if not mfa_settings.verify_totp(conn, db, user.id, code, stamp):
            conn.execute('UPDATE transfer_stepups SET attempts=?,attempt_window_start=? WHERE transfer_id=? AND session_id=?',
                (attempts + 1, window, transfer_id, user.session_id))
            security.failure(conn, user.id, stamp)
            audit(conn, user.id, 'TRANSFER_STEP_UP_REJECTED', stamp)
            from .mfa import invalid
            rejection = invalid()
        else:
            expiry = min(stamp + PROOF_SECONDS, int(datetime.fromisoformat(transfers._expires_at(transfer)).timestamp()))
            conn.execute('''UPDATE transfer_stepups SET auth_version=?,fingerprint=?,factor_hash=?,verified_at=?,expires_at=?,attempts=0,
                attempt_window_start=? WHERE transfer_id=? AND session_id=?''',
                (user.auth_version, fingerprint(transfer), _factor(conn, user.id), stamp, expiry, stamp, transfer_id, user.session_id))
            security.clear_failures(conn, user.id)
            audit(conn, user.id, 'TRANSFER_STEP_UP_VERIFIED', stamp)
            state = status(conn, user, transfer)
    if rejection:
        raise rejection
    return state
