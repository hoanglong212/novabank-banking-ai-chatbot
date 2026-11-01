"""One atomic posting path. Caller owns the SQLite write transaction."""
import uuid
from datetime import datetime, timedelta, timezone

VIETNAM = timezone(timedelta(hours=7))


class TransferError(Exception):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def business_day(stamp: str) -> str:
    return datetime.fromisoformat(stamp).astimezone(VIETNAM).date().isoformat()


def validate_accounts(conn, t: dict):
    source = conn.execute('SELECT * FROM accounts WHERE id=? AND owner_id=?',
                          (t['from_account'], t['owner_id'])).fetchone()
    if source is None:
        raise TransferError('ACCOUNT_NOT_OWNED')
    if source['status'] != 'ACTIVE':
        raise TransferError('ACCOUNT_NOT_ACTIVE')
    target = None
    if t['internal']:
        target = conn.execute('SELECT * FROM accounts WHERE id=?', (t['to_account'],)).fetchone()
        if target is None:
            raise TransferError('RECIPIENT_NOT_FOUND')
        if target['status'] != 'ACTIVE':
            raise TransferError('ACCOUNT_NOT_ACTIVE')
        if target['id'] == source['id']:
            raise TransferError('SAME_ACCOUNT')
    limit = int(conn.execute("SELECT value_json FROM bank_settings WHERE key='transfer_limit_vnd'").fetchone()[0])
    if type(t['amount_vnd']) is not int or not 1_000 <= t['amount_vnd'] <= limit:
        raise TransferError('INVALID_AMOUNT')
    if source['balance_vnd'] < t['amount_vnd'] + t.get('fee_vnd', 0):
        raise TransferError('INSUFFICIENT_FUNDS')
    return source, target


def audit(conn, owner: str, action: str, resource: str, reason: str, stamp: str,
          before: int | None = None, after: int | None = None):
    conn.execute('INSERT INTO banking_audit VALUES (?,?,?,?,?,?,?,?)',
                 (uuid.uuid4().hex, owner, action, resource, reason, before, after, stamp))


def post_journal(conn, journal_id: str, entries: list[tuple[str, int]], stamp: str, *, allow_frozen_credit=False):
    """Single primitive for transfers, products, fees and compensating entries.

    Caller owns BEGIN IMMEDIATE. Validate the entire journal before writing;
    customer cache updates and journal entries share that same transaction.
    """
    if not conn.in_transaction:
        raise RuntimeError('Posting requires an existing write transaction')
    if (len(entries) < 2 or len({a for a, _ in entries}) != len(entries)
            or any(type(n) is not int or n == 0 for _, n in entries) or sum(n for _, n in entries) != 0):
        raise TransferError('LEDGER_MISMATCH')
    for account_id, delta in entries:
        ledger = conn.execute('SELECT * FROM ledger_accounts WHERE id=?', (account_id,)).fetchone()
        if ledger is None:
            raise TransferError('LEDGER_MISMATCH')
        if ledger['customer_account_id']:
            account = conn.execute('SELECT * FROM accounts WHERE id=?', (ledger['customer_account_id'],)).fetchone()
            balance = conn.execute('SELECT COALESCE(SUM(amount_vnd),0) FROM ledger_entries WHERE account_id=?', (account_id,)).fetchone()[0]
            if account['balance_vnd'] != balance:
                raise TransferError('LEDGER_MISMATCH')
            if account['status'] != 'ACTIVE' and not (allow_frozen_credit and delta > 0 and account['status'] == 'FROZEN'):
                raise TransferError('ACCOUNT_NOT_ACTIVE')
            if balance + delta < 0:
                raise TransferError('INSUFFICIENT_FUNDS')
    for account_id, delta in entries:
        conn.execute('UPDATE accounts SET balance_vnd=balance_vnd+? WHERE id=(SELECT customer_account_id FROM ledger_accounts WHERE id=?)', (delta, account_id))
        conn.execute('INSERT INTO ledger_entries VALUES (?,?,?,?,?)', (uuid.uuid4().hex, journal_id, account_id, delta, stamp))


def _record_detail_and_notification(conn, tx_id: str, t: dict, account, balance: int,
                                    incoming: bool, counterparty: tuple[str, str, str], stamp: str):
    conn.execute('INSERT INTO transaction_details VALUES (?,?,?,?,?,?,?)',
                 (tx_id, t['id'], balance, *counterparty, 0 if incoming else t.get('fee_vnd', 0)))
    title = 'Money received' if incoming else ('Money sent' if t['internal'] else 'Transfer pending')
    direction = 'from' if incoming else 'to'
    name = counterparty[0] or counterparty[2]
    body = f'{t["amount_vnd"]:,} VND {direction} {name}.'
    conn.execute('INSERT INTO notifications VALUES (?,?,?,?,?,?,?,NULL)',
                 (uuid.uuid4().hex, account['owner_id'], tx_id, 'MONEY_IN' if incoming else 'MONEY_OUT', title, body, stamp))


def post_transfer(conn, t: dict, stamp: str) -> dict:
    """Balances, history, journal and successful audit commit together or roll back."""
    if not conn.in_transaction:
        raise RuntimeError('Posting requires an existing write transaction')
    source, target = validate_accounts(conn, t)
    for account in (source, target):
        if account is None:
            continue
        ledger_balance = conn.execute('''SELECT COALESCE(SUM(e.amount_vnd),0) FROM ledger_accounts l
                                        LEFT JOIN ledger_entries e ON e.account_id=l.id
                                        WHERE l.customer_account_id=? GROUP BY l.id''', (account['id'],)).fetchone()
        if ledger_balance is None or ledger_balance[0] != account['balance_vnd']:
            raise TransferError('LEDGER_MISMATCH')
    amount = t['amount_vnd']
    fee = t.get('fee_vnd', 0)
    tx_id = 'TX-' + uuid.uuid4().hex.upper()
    day = business_day(stamp)
    entries = [(source['id'], -amount - fee), (target['id'] if target else 'SYS-CLEARING', amount)]
    if fee:
        entries.append(('SYS-FEES', fee))
    post_journal(conn, t['id'], entries, stamp)
    count, total = conn.execute('SELECT COUNT(*),SUM(amount_vnd) FROM ledger_entries WHERE journal_id=?',
                                (t['id'],)).fetchone()
    if count < 2 or total != 0:
        raise TransferError('LEDGER_MISMATCH')
    recipient = t['to_name'] or f'{t["to_bank"]} ••••{t["to_account"][-4:]}'
    conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)', (
        tx_id, source['id'], amount, 'out', 'COMPLETED' if target else 'PENDING', f'Transfer to {recipient} · {t["content"]}', day, stamp))
    _record_detail_and_notification(conn, tx_id, t, source, source['balance_vnd'] - amount - fee, False,
                                    (t['to_name'], t['to_account'], t['to_bank']), stamp)
    if target:
        incoming_id = 'TX-' + uuid.uuid4().hex.upper()
        conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)', (
            incoming_id, target['id'], amount, 'in', 'COMPLETED',
            f'Transfer from {source["holder_name"]} · {t["content"]}', day, stamp))
        _record_detail_and_notification(conn, incoming_id, t, target, target['balance_vnd'] + amount, True,
                                        (source['holder_name'], source['id'], 'NovaBank'), stamp)
    balance = source['balance_vnd'] - amount - fee
    audit(conn, t['owner_id'], 'TRANSFER_COMPLETED' if target else 'TRANSFER_SUBMITTED', t['id'], 'POSTED', stamp, source['balance_vnd'], balance)
    if target:
        from .insights import budgets_after_posting
        budgets_after_posting(conn, t['owner_id'], day)
    return {'transaction_id': tx_id, 'balance_vnd': balance}
