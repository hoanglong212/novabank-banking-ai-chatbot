"""Bounded, owner-scoped financial read models. No writes to financial history."""
from datetime import date
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field


class TransactionQuery(BaseModel):
    q: str = Field(default='', max_length=100)
    recipient: str = Field(default='', max_length=100)
    account_id: str | None = Field(default=None, max_length=40)
    direction: Literal['in', 'out'] | None = None
    status: Literal['COMPLETED', 'PENDING', 'FAILED'] | None = None
    from_date: date | None = None
    to_date: date | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


JOINS = '''FROM transactions t JOIN accounts a ON a.id=t.account_id
           LEFT JOIN transaction_details d ON d.transaction_id=t.id
           LEFT JOIN product_transaction_details p ON p.transaction_id=t.id'''
COLUMNS = '''t.*,a.owner_id,a.holder_name,d.transfer_id,COALESCE(d.balance_after_vnd,p.balance_after_vnd) AS balance_after_vnd,
             COALESCE(d.counterparty_name,p.counterparty_name) AS counterparty_name,
             d.counterparty_account,d.counterparty_bank,COALESCE(d.fee_vnd,p.fee_vnd) AS fee_vnd,
             p.kind AS product_kind,p.resource_id'''


def transactions(db, query: TransactionQuery, owner_id: str | None) -> dict:
    if query.from_date and query.to_date and query.from_date > query.to_date:
        raise HTTPException(400, 'Start date must not be after end date')
    clauses, values = [], []
    if owner_id is not None:
        clauses.append('a.owner_id=?')
        values.append(owner_id)
    with db.connect() as conn:
        conn.execute('BEGIN')
        if query.account_id:
            account = conn.execute('SELECT owner_id FROM accounts WHERE id=?', (query.account_id,)).fetchone()
            if not account or (owner_id is not None and account['owner_id'] != owner_id):
                raise HTTPException(404, 'Account not found')
            clauses.append('t.account_id=?')
            values.append(query.account_id)
        for field in ('direction', 'status'):
            value = getattr(query, field)
            if value:
                clauses.append(f't.{field}=?')
                values.append(value)
        for field, operator in (('from_date', '>='), ('to_date', '<=')):
            value = getattr(query, field)
            if value:
                clauses.append(f't.date{operator}?')
                values.append(value.isoformat())
        if query.q.strip():
            escaped = query.q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            clauses.append("(t.id LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\' OR t.account_id LIKE ? ESCAPE '\\')")
            values.extend(['%' + escaped + '%'] * 3)
        if query.recipient.strip():
            escaped = query.recipient.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            clauses.append("(d.counterparty_account LIKE ? ESCAPE '\\' OR COALESCE(d.counterparty_name,p.counterparty_name,t.description) LIKE ? ESCAPE '\\')")
            values.extend(['%' + escaped + '%'] * 2)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        total = conn.execute('SELECT COUNT(*) ' + JOINS + where, values).fetchone()[0]
        rows = conn.execute('SELECT ' + COLUMNS + ' ' + JOINS + where +
                            ' ORDER BY t.date DESC,t.created_at DESC,t.id DESC LIMIT ? OFFSET ?',
                            (*values, query.limit, query.offset)).fetchall()
        return {'items': [dict(row) for row in rows], 'total': total, 'limit': query.limit, 'offset': query.offset}


def transaction(db, transaction_id: str, owner_id: str) -> dict:
    with db.connect() as conn:
        row = conn.execute('SELECT ' + COLUMNS + ' ' + JOINS + ' WHERE t.id=? AND a.owner_id=?',
                           (transaction_id, owner_id)).fetchone()
        if row is None:
            raise HTTPException(404, 'Transaction not found')
        return dict(row)


# Personal alerts split into two tabs; everything that is not money movement is about the account.
CATEGORY_SQL = "CASE WHEN kind IN ('MONEY_IN','MONEY_OUT','TRANSFER','REFUND','BILL') THEN 'transactions' ELSE 'account' END"
NOTIFICATION_SOURCE = f"""(SELECT *, {CATEGORY_SQL} AS category FROM
    (SELECT id,owner_id,transaction_id,kind,title,body,created_at,read_at FROM notifications
     UNION ALL SELECT id,owner_id,transaction_id,kind,title,body,created_at,read_at FROM service_notifications))"""


def notifications(db, owner_id: str, limit: int, offset: int, category: str | None = None,
                  q: str = '', unread: bool = False) -> dict:
    clauses, params = ['owner_id=?'], [owner_id]
    if category:
        clauses.append('category=?'); params.append(category)
    if q.strip():
        # Same escaping as transaction search: % and _ in the query are literal.
        escaped = '%' + q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        clauses.append("(title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\')"); params += [escaped, escaped]
    if unread:
        clauses.append('read_at IS NULL')
    where, params = ' AND '.join(clauses), tuple(params)
    with db.connect() as conn:
        conn.execute('BEGIN')
        total, unread = conn.execute(f'SELECT COUNT(*),COALESCE(SUM(read_at IS NULL),0) FROM {NOTIFICATION_SOURCE} WHERE {where}',
                                     params).fetchone()
        rows = conn.execute(f'SELECT * FROM {NOTIFICATION_SOURCE} WHERE {where} ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?',
                            (*params, limit, offset)).fetchall()
        by_category = dict(conn.execute(f'SELECT category,SUM(read_at IS NULL) FROM {NOTIFICATION_SOURCE} WHERE owner_id=? GROUP BY category',
                                        (owner_id,)).fetchall())
        return {'items': [dict(row) for row in rows], 'total': total, 'unread_count': unread, 'limit': limit, 'offset': offset,
                'unread_by_category': {name: by_category.get(name, 0) for name in ('transactions', 'account')}}


# Bank-wide news is kept apart from personal alerts so campaigns never inflate the unread badge.
# shortcut: fixed fictional seed with no staff editor; add an operations screen when staff must publish news.
ANNOUNCEMENTS = [
    ('ANN-2026-11-CASHBACK', 'CAMPAIGN', 'Pay bills, get 5% back', 'Cashback 5%',
     'Pay electricity, water, internet or mobile bills with NovaBank before 30 November and get 5% back, up to 50,000 VND a month.',
     'Pay a bill', '/explore/bills', '2026-11-01T01:00:00+00:00', '2026-11-30T16:59:59+00:00'),
    ('ANN-2026-11-SAVINGS', 'CAMPAIGN', 'Term savings at 6.2% a year', '6.2% / year',
     'Open a 12-month online term deposit from 1,000,000 VND. Interest is paid at maturity and you can close early at any time.',
     'Open savings', '/explore/savings', '2026-11-03T02:00:00+00:00', '2026-12-31T16:59:59+00:00'),
    ('ANN-2026-11-QRPAY', 'CAMPAIGN', 'Pay friends with QR Pay', 'Free',
     'Scan a NovaBank QR to pay instantly. Transfers between NovaBank accounts are always free.',
     'Open QR Pay', '/qr', '2026-11-05T03:00:00+00:00', None),
    ('ANN-2026-11-MAINTENANCE', 'NOTICE', 'Scheduled maintenance on 15 November', 'Service notice',
     'Some services may be unavailable from 23:00 on 15 November to 01:00 on 16 November, Vietnam time. Card payments keep working.',
     None, None, '2026-11-06T04:00:00+00:00', '2026-11-15T18:00:00+00:00'),
    ('ANN-2026-10-OTP', 'NOTICE', 'NovaBank never asks for your OTP', 'Security',
     'We never ask for verification codes by phone, SMS or chat. If someone does, stop and contact Support.',
     'Contact support', '/explore/support', '2026-10-20T02:00:00+00:00', None),
]


def initialize_announcements(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS bank_announcements (id TEXT PRIMARY KEY,
        kind TEXT NOT NULL CHECK(kind IN ('CAMPAIGN','NOTICE')), title TEXT NOT NULL, tag TEXT NOT NULL, body TEXT NOT NULL,
        action_label TEXT, action_path TEXT, published_at TEXT NOT NULL, ends_at TEXT)""")
    conn.executemany('INSERT OR IGNORE INTO bank_announcements VALUES (?,?,?,?,?,?,?,?,?)', ANNOUNCEMENTS)


def announcements(db, stamp: str) -> dict:
    with db.connect() as conn:
        rows = conn.execute('SELECT * FROM bank_announcements WHERE published_at<=? AND (ends_at IS NULL OR ends_at>?) '
                            'ORDER BY published_at DESC', (stamp, stamp)).fetchall()
        return {'items': [dict(row) for row in rows]}
