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


def notifications(db, owner_id: str, limit: int, offset: int) -> dict:
    with db.connect() as conn:
        conn.execute('BEGIN')
        source = '''(SELECT id,owner_id,transaction_id,kind,title,body,created_at,read_at FROM notifications
                     UNION ALL SELECT id,owner_id,transaction_id,kind,title,body,created_at,read_at FROM service_notifications)'''
        total, unread = conn.execute('SELECT COUNT(*),COALESCE(SUM(read_at IS NULL),0) FROM ' + source + ' WHERE owner_id=?',
                                     (owner_id,)).fetchone()
        rows = conn.execute('SELECT * FROM ' + source + ' WHERE owner_id=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?',
                            (owner_id, limit, offset)).fetchall()
        return {'items': [dict(row) for row in rows], 'total': total, 'unread_count': unread, 'limit': limit, 'offset': offset}
