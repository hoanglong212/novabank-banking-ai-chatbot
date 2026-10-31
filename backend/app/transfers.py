"""Simulated money movement: draft -> OTP -> one atomic posting.

The assistant can only create drafts (create_transfer tool). Completing a transfer needs the OTP,
which is shown only in the app's simulated SMS, never to the model, and the input guard redacts
OTPs typed into chat. Nothing here touches a real bank or NAPAS.
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from . import vietqr
from .auth import DemoPrincipal
from .database import Database, now
from .faq import fold

NOVABANK = {'novabank', 'nova', 'nvb'}
DAILY_LIMIT_VND = 200_000_000
OTP_TTL = timedelta(minutes=2)
MAX_OTP_ATTEMPTS = 3


class TransferError(Exception):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _otp_hash(transfer_id: str, otp: str) -> str:
    return hashlib.sha256(f'{transfer_id}:{otp}'.encode()).hexdigest()


def public(transfer: dict) -> dict:
    return {k: transfer[k] for k in ('id', 'from_account', 'to_bank', 'to_account', 'to_name', 'amount_vnd',
                                     'content', 'status', 'otp_expires_at', 'transaction_id') if k in transfer}


async def prepare(db: Database, user: DemoPrincipal, args: dict) -> dict:
    """Validate and store a PENDING_OTP draft. args are already validated by TransferArgs. No money moves."""
    source = args.get('from_account') or user.accounts[0]
    if source not in user.accounts:
        raise TransferError('ACCOUNT_NOT_OWNED')
    if fold(args['to_bank']).replace(' ', '') in NOVABANK:
        target = db.account(args['to_account'].upper())
        if target is None:
            raise TransferError('RECIPIENT_NOT_FOUND')
        if target['id'] == source:
            raise TransferError('SAME_ACCOUNT')
        # Name inquiry, as in every banking app: the payer sees the holder name before confirming.
        bank, account, name, internal = 'NovaBank', target['id'], target['holder_name'], True
    else:
        if not args['to_account'].isdigit():
            raise TransferError('INVALID_ACCOUNT')
        try:
            found = vietqr.find_bank(await vietqr.banks(), args['to_bank'])
        except vietqr.VietQRError as exc:
            raise TransferError(exc.reason_code) from exc
        if found is None:
            raise TransferError('UNKNOWN_BANK')
        # shortcut: interbank name inquiry is not simulated; the payer-supplied name is shown as unverified.
        bank, account, name, internal = found['shortName'], args['to_account'], \
            vietqr.plain(args.get('to_name') or '', 50).upper(), False
    if db.account(source)['balance_vnd'] < args['amount_vnd']:
        raise TransferError('INSUFFICIENT_FUNDS')
    transfer = dict(id='TRF-' + uuid.uuid4().hex[:8].upper(), owner_id=user.id, from_account=source, to_bank=bank,
                    to_account=account, to_name=name, internal=int(internal), amount_vnd=args['amount_vnd'],
                    content=vietqr.plain(args.get('content') or f'{user.name} transfer', 25) or 'Transfer',
                    status='PENDING_OTP', created_at=now())
    db.create_transfer(transfer)
    return transfer


def issue_otp(db: Database, user: DemoPrincipal, transfer_id: str) -> tuple[dict, str]:
    """(Re)send the simulated SMS OTP. Returns the draft and the OTP, which only the app UI may show."""
    otp = f'{secrets.randbelow(10**6):06d}'
    expires = (datetime.now(timezone.utc) + OTP_TTL).isoformat(timespec='seconds')
    with db.connect() as conn:
        updated = conn.execute("UPDATE transfers SET otp_hash=?, otp_expires_at=? WHERE id=? AND owner_id=? "
                               "AND status='PENDING_OTP'", (_otp_hash(transfer_id, otp), expires, transfer_id, user.id))
    if updated.rowcount != 1:
        raise TransferError('TRANSFER_NOT_FOUND' if db.get_transfer(transfer_id, user.id) is None else 'ALREADY_PROCESSED')
    return db.get_transfer(transfer_id, user.id), otp


def confirm(db: Database, user: DemoPrincipal, transfer_id: str, otp: str) -> dict:
    transfer = db.get_transfer(transfer_id, user.id)
    if transfer is None:
        raise TransferError('TRANSFER_NOT_FOUND')
    if transfer['status'] != 'PENDING_OTP':
        raise TransferError('ALREADY_PROCESSED')
    if not transfer['otp_hash']:
        raise TransferError('OTP_REQUIRED')
    if transfer['otp_expires_at'] < now():
        raise TransferError('OTP_EXPIRED')
    if not hmac.compare_digest(transfer['otp_hash'], _otp_hash(transfer_id, otp)):
        with db.connect() as conn:
            conn.execute("UPDATE transfers SET otp_attempts=otp_attempts+1, status=CASE WHEN otp_attempts+1>=? "
                         "THEN 'FAILED' ELSE status END WHERE id=?", (MAX_OTP_ATTEMPTS, transfer_id))
        raise TransferError('OTP_LOCKED' if transfer['otp_attempts'] + 1 >= MAX_OTP_ATTEMPTS else 'OTP_INVALID')
    try:
        return _post(db, transfer)
    except TransferError:
        with db.connect() as conn:
            conn.execute("UPDATE transfers SET status='FAILED' WHERE id=? AND status='PENDING_OTP'", (transfer_id,))
        raise


def _post(db: Database, t: dict) -> dict:
    """Debit, credit and both ledger lines in one SQLite transaction; any failure rolls all of it back."""
    stamp, today = now(), now()[:10]
    tx_id = 'TX-' + uuid.uuid4().hex[:8].upper()
    with db.connect() as conn:
        # Claiming the draft first makes a double confirm (double click, replay) post at most once.
        if conn.execute("UPDATE transfers SET status='COMPLETED', otp_hash=NULL, transaction_id=?, completed_at=? "
                        "WHERE id=? AND status='PENDING_OTP'", (tx_id, stamp, t['id'])).rowcount != 1:
            raise TransferError('ALREADY_PROCESSED')
        spent = conn.execute("SELECT COALESCE(SUM(amount_vnd),0) FROM transfers WHERE owner_id=? AND status='COMPLETED' "
                             "AND substr(completed_at,1,10)=?", (t['owner_id'], today)).fetchone()[0]
        if spent > DAILY_LIMIT_VND:
            raise TransferError('DAILY_LIMIT_EXCEEDED')
        if conn.execute('UPDATE accounts SET balance_vnd=balance_vnd-? WHERE id=? AND balance_vnd>=?',
                        (t['amount_vnd'], t['from_account'], t['amount_vnd'])).rowcount != 1:
            raise TransferError('INSUFFICIENT_FUNDS')
        recipient = t['to_name'] or f'{t["to_bank"]} ••••{t["to_account"][-4:]}'
        conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)', (
            tx_id, t['from_account'], t['amount_vnd'], 'out', 'COMPLETED', f'Transfer to {recipient} · {t["content"]}', today, stamp))
        if t['internal']:
            sender = conn.execute('SELECT holder_name FROM accounts WHERE id=?', (t['from_account'],)).fetchone()[0]
            conn.execute('UPDATE accounts SET balance_vnd=balance_vnd+? WHERE id=?', (t['amount_vnd'], t['to_account']))
            conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)', (
                'TX-' + uuid.uuid4().hex[:8].upper(), t['to_account'], t['amount_vnd'], 'in', 'COMPLETED',
                f'Transfer from {sender} · {t["content"]}', today, stamp))
        balance = conn.execute('SELECT balance_vnd FROM accounts WHERE id=?', (t['from_account'],)).fetchone()[0]
    return {**public({**t, 'status': 'COMPLETED', 'transaction_id': tx_id}), 'balance_vnd': balance}
