"""Fictional cards, bills and term savings, settled through the common journal."""
import calendar
from datetime import date, datetime, timezone
import uuid
from fastapi import HTTPException
from . import action_security
from .banking_schema import ensure_products
from .database import now
from .identity import transaction
from .posting import post_journal, audit, business_day, TransferError

RATES = {3: 450, 6: 500, 12: 600}


def owned(conn, table, resource, owner):
    if table not in ('cards', 'bills', 'savings', 'accounts', 'savings_goals'):
        raise ValueError('Invalid resource table')
    row = conn.execute(f'SELECT * FROM {table} WHERE id=? AND owner_id=?', (resource, owner)).fetchone()
    if row is None:
        raise HTTPException(404, 'Resource not found.')
    return dict(row)


def term_end(start: date, months: int):
    month = start.month - 1 + months
    year, month = start.year + month // 12, month % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1])).isoformat()


def projected(saving):
    return saving['principal_vnd'] * saving['rate_bps'] * saving['term_months'] // (10000 * 12)


def list_products(db, user, kind):
    if kind not in ('cards', 'bills', 'savings'):
        raise HTTPException(404, 'Product not found.')
    with transaction(db) as conn:
        ensure_products(conn, user.id, now())
        rows = [dict(r) for r in conn.execute(f'SELECT * FROM {kind} WHERE owner_id=? ORDER BY id', (user.id,))]
        if kind == 'cards':
            for row in rows:
                row['transactions'] = [dict(r) for r in conn.execute('SELECT * FROM card_transactions WHERE card_id=? ORDER BY created_at DESC,rowid DESC LIMIT 100', (row['id'],))]
        if kind == 'savings':
            for row in rows:
                row['projected_interest_vnd'] = projected(row)
                row['events'] = [dict(r) for r in conn.execute('SELECT * FROM savings_events WHERE savings_id=? ORDER BY created_at,rowid', (row['id'],))]
        return {'items': rows, 'rates_bps': RATES if kind == 'savings' else None}


def validate(conn, user, kind, payload):
    p = dict(payload)
    resource = p.get('resource_id')
    if kind == 'PAY_BILL':
        bill = owned(conn, 'bills', resource, user.id)
        if bill['status'] != 'UNPAID':
            raise HTTPException(409, 'Bill is already paid.')
        p.update(amount_vnd=bill['amount_vnd'], label=bill['provider'], category=bill['category'])
    elif kind == 'OPEN_SAVINGS':
        if p.get('term_months') not in RATES or p.get('amount_vnd', 0) < 100000:
            raise HTTPException(422, 'Choose 3, 6 or 12 months and at least 100,000 VND.')
    elif kind == 'WITHDRAW_SAVINGS':
        saving = owned(conn, 'savings', resource, user.id)
        if saving['status'] != 'ACTIVE':
            raise HTTPException(409, 'Savings account is closed.')
        # Destination is fixed to the original funding account, never supplied by an agent.
        p['account_id'] = saving['account_id']
        p['amount_vnd'] = saving['principal_vnd']
        p['label'] = saving['label']
        p['early_withdrawal_interest_vnd'] = 0
    elif kind in ('FREEZE_CARD', 'UNFREEZE_CARD', 'CARD_PURCHASE', 'REPAY_CARD'):
        card = owned(conn, 'cards', resource, user.id)
        p['account_id'] = card['account_id']
        if kind in ('FREEZE_CARD', 'UNFREEZE_CARD'):
            expected = 'ACTIVE' if kind == 'FREEZE_CARD' else 'FROZEN'
            if card['status'] != expected:
                raise HTTPException(409, 'Card state has changed. Refresh and try again.')
        elif kind == 'CARD_PURCHASE':
            if card['status'] != 'ACTIVE':
                raise HTTPException(409, 'Unfreeze this card before making a simulated purchase.')
            if card['kind'] == 'CREDIT' and card['outstanding_vnd'] + p.get('amount_vnd', 0) > card['credit_limit_vnd']:
                raise HTTPException(400, 'Credit limit exceeded.')
        elif card['kind'] != 'CREDIT' or not 0 < p.get('amount_vnd', 0) <= card['outstanding_vnd']:
            raise HTTPException(400, 'Repayment must not exceed the outstanding credit balance.')
    else:
        raise HTTPException(422, 'Unsupported product action.')
    if kind not in ('FREEZE_CARD', 'UNFREEZE_CARD'):
        account = owned(conn, 'accounts', p.get('account_id'), user.id)
        if account['status'] != 'ACTIVE':
            raise HTTPException(400, 'Payment account is not active.')
        amount = p.get('amount_vnd', 0)
        if type(amount) is not int or not 1000 <= amount <= 100000000:
            raise HTTPException(422, 'Amount must be an integer between 1,000 and 100,000,000 VND.')
        credit_purchase = kind == 'CARD_PURCHASE' and card['kind'] == 'CREDIT'
        if kind != 'WITHDRAW_SAVINGS' and not credit_purchase and account['balance_vnd'] < amount:
            raise HTTPException(400, 'Insufficient funds.')
    return p


def prepare(db, user, kind, payload):
    action_security.limit(db, user)
    with transaction(db) as conn:
        ensure_products(conn, user.id, now())
        p = validate(conn, user, kind, payload)
        return action_security.create(conn, user, kind, p)


def money(conn, user, account_id, amount, incoming, counter, journal, kind, resource, label, stamp, extra_entries=None):
    account = owned(conn, 'accounts', account_id, user.id)
    delta = amount if incoming else -amount
    entries = [(account_id, delta), (counter, -delta)] if extra_entries is None else extra_entries
    post_journal(conn, journal, entries, stamp)
    balance = conn.execute('SELECT balance_vnd FROM accounts WHERE id=?', (account_id,)).fetchone()[0]
    tx = 'TX-' + uuid.uuid4().hex.upper()
    conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)',
                 (tx, account_id, amount, 'in' if incoming else 'out', 'COMPLETED', label, business_day(stamp), stamp))
    conn.execute('INSERT INTO product_transaction_details VALUES (?,?,?,?,?,?,0)', (tx, journal, kind, resource, balance, label))
    action_security.notify(conn, user.id, 'MONEY_IN' if incoming else 'MONEY_OUT',
                           'Money received' if incoming else 'Payment completed', f'{amount:,} VND · {label}', stamp, resource, tx)
    audit(conn, user.id, kind, resource, 'POSTED', stamp, account['balance_vnd'], balance)
    return tx


def execute(conn, user, kind, payload, journal, seconds):
    p = validate(conn, user, kind, payload)  # Recheck ownership, funds and state under the posting lock.
    stamp = datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds')
    resource = p.get('resource_id', '')
    amount = p.get('amount_vnd', 0)
    tx = None
    try:
        if kind in ('FREEZE_CARD', 'UNFREEZE_CARD'):
            status = 'FROZEN' if kind == 'FREEZE_CARD' else 'ACTIVE'
            conn.execute('UPDATE cards SET status=? WHERE id=?', (status, resource))
            audit(conn, user.id, kind, resource, 'CONFIRMED', stamp)
            action_security.notify(conn, user.id, 'CARD', 'Card ' + status.lower(), 'Your simulated card status was updated.', stamp, resource)
        elif kind == 'PAY_BILL':
            tx = money(conn, user, p['account_id'], amount, False, 'SYS-BILLS', journal, kind, resource, p['label'], stamp)
            conn.execute("UPDATE bills SET status='PAID',transaction_id=?,paid_at=? WHERE id=?", (tx, stamp, resource))
            conn.execute('INSERT INTO transaction_categories VALUES (?,?)', (tx, p['category']))
        elif kind == 'OPEN_SAVINGS':
            resource = 'SAV-' + uuid.uuid4().hex[:12].upper()
            months = p['term_months']
            conn.execute('INSERT INTO savings VALUES (?,?,?,?,?,?,?,?,?,\'ACTIVE\',NULL,0)',
                         (resource, user.id, p['account_id'], p.get('label') or 'Term savings', amount, months,
                          RATES[months], stamp, term_end(date.fromisoformat(stamp[:10]), months)))
            tx = money(conn, user, p['account_id'], amount, False, 'SYS-SAVINGS', journal, kind, resource, 'Savings deposit · ' + p.get('label', ''), stamp)
            conn.execute('INSERT INTO savings_events VALUES (?,?,?,?,?,?)', (uuid.uuid4().hex, resource, 'OPEN', amount, tx, stamp))
        elif kind == 'WITHDRAW_SAVINGS':
            saving = owned(conn, 'savings', resource, user.id)
            interest = projected(saving) if stamp[:10] >= saving['maturity_date'] else 0
            entries = [(p['account_id'], amount + interest), ('SYS-SAVINGS', -amount)]
            if interest:
                entries.append(('SYS-INTEREST', -interest))
            tx = money(conn, user, p['account_id'], amount + interest, True, 'SYS-SAVINGS', journal, kind, resource,
                       'Savings withdrawal · ' + saving['label'], stamp, entries)
            conn.execute("UPDATE savings SET status='CLOSED',closed_at=?,interest_paid_vnd=? WHERE id=?", (stamp, interest, resource))
            conn.execute('INSERT INTO savings_events VALUES (?,?,?,?,?,?)', (uuid.uuid4().hex, resource, 'CLOSE', amount + interest, tx, stamp))
        elif kind in ('CARD_PURCHASE', 'REPAY_CARD'):
            card = owned(conn, 'cards', resource, user.id)
            label = p.get('label') or ('Credit repayment' if kind == 'REPAY_CARD' else 'Simulated purchase')
            if kind == 'REPAY_CARD':
                tx = money(conn, user, card['account_id'], amount, False, 'CREDIT:' + resource, journal, kind, resource, label, stamp)
                conn.execute('UPDATE cards SET outstanding_vnd=outstanding_vnd-? WHERE id=?', (amount, resource))
            elif card['kind'] == 'CREDIT':
                post_journal(conn, journal, [('CREDIT:' + resource, -amount), ('SYS-MERCHANTS', amount)], stamp)
                conn.execute('UPDATE cards SET outstanding_vnd=outstanding_vnd+? WHERE id=?', (amount, resource))
                audit(conn, user.id, kind, resource, 'CREDIT_POSTED', stamp)
                action_security.notify(conn, user.id, 'CARD', 'Credit card purchase', f'{amount:,} VND · {label}', stamp, resource)
            else:
                tx = money(conn, user, card['account_id'], amount, False, 'SYS-MERCHANTS', journal, kind, resource, label, stamp)
            conn.execute('INSERT INTO card_transactions VALUES (?,?,?,?,?,?,?)', (uuid.uuid4().hex, resource, amount, kind, label, journal, stamp))
    except TransferError as exc:
        raise HTTPException(400 if exc.reason_code != 'LEDGER_MISMATCH' else 503, exc.reason_code) from exc
    from .insights import budgets_after_posting
    budgets_after_posting(conn, user.id, business_day(stamp))
    return {'message': 'Action completed.', 'kind': kind, 'resource_id': resource, 'transaction_id': tx}
