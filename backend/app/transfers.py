"""Simulated drafts and OTP-confirmed, idempotent money movement.

The agent only has prepare(), never an OTP or a confirmation tool.
No payment here touches a real bank or NAPAS.
"""
import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from . import vietqr
from .auth import DemoPrincipal
from .database import Database, now
from .faq import fold
from .posting import TransferError, VIETNAM, audit, post_transfer, validate_accounts

NOVABANK = {'novabank', 'nova', 'nvb'}
DAILY_LIMIT_VND = 200_000_000
OTP_TTL = timedelta(minutes=2)
DRAFT_TTL = timedelta(minutes=5)
MAX_OTP_ATTEMPTS = 3


def _otp_hash(transfer_id: str, otp: str) -> str:
    return hashlib.sha256(f'{transfer_id}:{otp}'.encode()).hexdigest()


def _expires_at(transfer: dict) -> str:
    return (datetime.fromisoformat(transfer['created_at']) + DRAFT_TTL).isoformat(timespec='seconds')


def public(transfer: dict) -> dict:
    result = {k: transfer[k] for k in ('id', 'from_account', 'to_bank', 'to_account', 'to_name', 'amount_vnd',
                                      'content', 'status', 'otp_expires_at', 'transaction_id', 'fee_vnd') if k in transfer}
    if transfer.get('settlement_status'):
        result['status'] = transfer['settlement_status']
    if 'created_at' in transfer:
        result['expires_at'] = _expires_at(transfer)
    return result


def _check_daily_limit(conn, owner_id: str, amount: int, stamp: str):
    local = datetime.fromisoformat(stamp).astimezone(VIETNAM)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    bounds = [d.astimezone(timezone.utc).isoformat(timespec='seconds') for d in (start, start + timedelta(days=1))]
    spent = conn.execute("SELECT COALESCE(SUM(amount_vnd),0) FROM transfers WHERE owner_id=? AND status='COMPLETED' "
                         'AND completed_at>=? AND completed_at<?', (owner_id, *bounds)).fetchone()[0]
    configured = int(conn.execute("SELECT value_json FROM bank_settings WHERE key='daily_limit_vnd'").fetchone()[0])
    if spent + amount > min(DAILY_LIMIT_VND, configured):
        raise TransferError('DAILY_LIMIT_EXCEEDED')


async def prepare(db: Database, user: DemoPrincipal, args: dict) -> dict:
    """Create a five-minute draft after schema validation. No money moves."""
    from .recipient_security import limit
    limit(db, user)
    source = args.get('from_account') or user.accounts[0]
    if source not in user.accounts:
        raise TransferError('ACCOUNT_NOT_OWNED')
    internal = fold(args['to_bank']).replace(' ', '') in NOVABANK
    bank, account, name = 'NovaBank', args['to_account'].upper(), ''
    if not internal:
        if not args['to_account'].isdigit():
            raise TransferError('INVALID_ACCOUNT')
        try:
            found = vietqr.find_bank(await vietqr.banks(), args['to_bank'])
        except vietqr.VietQRError as exc:
            raise TransferError(exc.reason_code) from exc
        if found is None:
            raise TransferError('UNKNOWN_BANK')
        bank, account, name = found['shortName'], args['to_account'], vietqr.plain(args.get('to_name') or '', 50).upper()
    transfer = dict(id='TRF-' + uuid.uuid4().hex.upper(), owner_id=user.id, from_account=source, to_bank=bank,
                    to_account=account, to_name=name, internal=int(internal), amount_vnd=args['amount_vnd'],
                    # Customer prose is data, not a QR field. React/PDF escape when rendering.
                    content=(args.get('content') or f'{user.name} transfer').strip()[:80] or 'Transfer',
                    status='PENDING_OTP', created_at=now())
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        from .settlement import fee
        transfer['fee_vnd'] = fee(conn)
        _, target = validate_accounts(conn, transfer)
        _check_daily_limit(conn, user.id, transfer['amount_vnd'], transfer['created_at'])
        if target:
            transfer['to_name'] = target['holder_name']
        conn.execute('INSERT INTO transfers (id,owner_id,from_account,to_bank,to_account,to_name,internal,amount_vnd,'
                     'content,status,created_at) VALUES (:id,:owner_id,:from_account,:to_bank,:to_account,:to_name,'
                     ':internal,:amount_vnd,:content,:status,:created_at)', transfer)
        conn.execute('INSERT INTO transfer_quotes VALUES (?,?)', (transfer['id'], transfer['fee_vnd']))
    return transfer


def _own_transfer(conn, transfer_id: str, user: DemoPrincipal) -> dict:
    row = conn.execute('''SELECT t.*,COALESCE(q.fee_vnd,0) AS fee_vnd,s.status AS settlement_status FROM transfers t
        LEFT JOIN transfer_quotes q ON q.transfer_id=t.id LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
        WHERE t.id=? AND t.owner_id=?''', (transfer_id, user.id)).fetchone()
    if row is None:
        raise TransferError('TRANSFER_NOT_FOUND')
    return dict(row)


def _fail(conn, t: dict, reason: str, stamp: str):
    changed = conn.execute("UPDATE transfers SET status='FAILED',failure_reason=?,otp_hash=NULL "
                           "WHERE id=? AND status='PENDING_OTP'", (reason, t['id']))
    if changed.rowcount:
        conn.execute('UPDATE dev_outbox SET secret_text=NULL WHERE challenge_id=?', ('transfer:' + t['id'],))
        audit(conn, t['owner_id'], 'TRANSFER_FAILED', t['id'], reason, stamp)


def issue_otp(db: Database, user: DemoPrincipal, transfer_id: str) -> tuple[dict, str]:
    """Resend replaces the previous OTP; it never resets attempts or extends the draft."""
    error = None
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        t = _own_transfer(conn, transfer_id, user)
        stamp = now()
        if t['status'] != 'PENDING_OTP':
            raise TransferError('ALREADY_PROCESSED')
        if _expires_at(t) <= stamp:
            _fail(conn, t, 'DRAFT_EXPIRED', stamp)
            error = TransferError('DRAFT_EXPIRED')
        else:
            otp = f'{secrets.randbelow(10**6):06d}'
            expires = min((datetime.fromisoformat(stamp) + OTP_TTL).isoformat(timespec='seconds'), _expires_at(t))
            conn.execute('UPDATE transfers SET otp_hash=?,otp_expires_at=? WHERE id=?',
                         (_otp_hash(transfer_id, otp), expires, transfer_id))
            conn.execute('UPDATE dev_outbox SET secret_text=NULL WHERE challenge_id=?', ('transfer:' + transfer_id,))
            email = conn.execute('SELECT email FROM users WHERE id=?', (user.id,)).fetchone()[0]
            conn.execute('''INSERT INTO dev_outbox
                (id,user_id,recipient,kind,created_at,expires_at,secret_text,challenge_id,body)
                VALUES (?,?,?,'TRANSFER_OTP',?,?,?,?,?)''',
                (uuid.uuid4().hex, user.id, email, int(datetime.fromisoformat(stamp).timestamp()),
                 int(datetime.fromisoformat(expires).timestamp()), otp, 'transfer:' + transfer_id,
                 'Verification code for transfer ' + transfer_id + '. Enter it only in the bank confirmation screen.'))
            t = {**t, 'otp_expires_at': expires}
    if error:
        raise error
    return t, otp


def _confirm_locked(conn, user: DemoPrincipal, transfer_id: str, otp: str, key: str | None):
    t = _own_transfer(conn, transfer_id, user)
    if key is not None:
        previous = conn.execute('SELECT * FROM idempotency_keys WHERE owner_id=? AND key=?', (user.id, key)).fetchone()
        if previous:
            if previous['transfer_id'] != transfer_id:
                raise TransferError('IDEMPOTENCY_CONFLICT')
            # Authenticated receipt retrieval: never persist the OTP in the retry cache.
            return json.loads(previous['response_json'])
    if t['status'] != 'PENDING_OTP':
        raise TransferError('ALREADY_PROCESSED')
    stamp = now()  # Read time after acquiring the write lock.
    if _expires_at(t) <= stamp:
        _fail(conn, t, 'DRAFT_EXPIRED', stamp)
        return TransferError('DRAFT_EXPIRED')
    if not t['otp_hash']:
        return TransferError('OTP_REQUIRED')
    if t['otp_expires_at'] <= stamp:
        return TransferError('OTP_EXPIRED')
    if not hmac.compare_digest(t['otp_hash'], _otp_hash(transfer_id, otp)):
        attempts = t['otp_attempts'] + 1
        conn.execute('UPDATE transfers SET otp_attempts=? WHERE id=?', (attempts, transfer_id))
        if attempts >= MAX_OTP_ATTEMPTS:
            _fail(conn, t, 'OTP_LOCKED', stamp)
            return TransferError('OTP_LOCKED')
        audit(conn, user.id, 'OTP_REJECTED', transfer_id, 'OTP_INVALID', stamp)
        return TransferError('OTP_INVALID')
    _check_daily_limit(conn, user.id, t['amount_vnd'], stamp)
    posted = post_transfer(conn, t, stamp)
    conn.execute('UPDATE dev_outbox SET secret_text=NULL WHERE challenge_id=?', ('transfer:' + transfer_id,))
    conn.execute("UPDATE transfers SET status='COMPLETED',otp_hash=NULL,transaction_id=?,completed_at=? WHERE id=?",
                 (posted['transaction_id'], stamp, transfer_id))
    if not t['internal']:
        from .settlement import enqueue
        enqueue(conn, transfer_id, stamp)
        t['settlement_status'] = 'PENDING'
    result = {**public({**t, 'status': 'COMPLETED', 'transaction_id': posted['transaction_id']}), **posted}
    if key is not None:
        conn.execute('INSERT INTO idempotency_keys VALUES (?,?,?,?,?)',
                     (user.id, key, transfer_id, json.dumps(result), stamp))
    return result


def confirm(db: Database, user: DemoPrincipal, transfer_id: str, otp: str, idempotency_key: str | None = None) -> dict:
    """Serialize OTP validation, mutable rules, posting and receipt persistence."""
    try:
        with db.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            result = _confirm_locked(conn, user, transfer_id, otp, idempotency_key)
    except (TransferError, sqlite3.Error) as exc:
        reason = exc.reason_code if isinstance(exc, TransferError) else 'POSTING_FAILED'
        if reason in {'INSUFFICIENT_FUNDS', 'DAILY_LIMIT_EXCEEDED', 'ACCOUNT_NOT_ACTIVE',
                      'RECIPIENT_NOT_FOUND', 'LEDGER_MISMATCH', 'POSTING_FAILED'}:
            # Financial effects rolled back; do not overwrite a concurrently completed retry.
            try:
                with db.connect() as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    t = _own_transfer(conn, transfer_id, user)
                    _fail(conn, t, reason, now())
            except sqlite3.Error:
                pass  # Unavailable storage may prevent recording failure too.
        raise TransferError(reason) from exc
    if isinstance(result, TransferError):
        # Attempt count/failed status committed before reporting OTP rejection.
        raise result
    return result
