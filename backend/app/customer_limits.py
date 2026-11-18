"""Customer-selected transfer cap, bounded by bank policy and confirmed in the app."""
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import Field
from .identity_schemas import IdentityInput


class LimitArgs(IdentityInput):
    limit_vnd: int = Field(ge=1000, le=1000000000)


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=19').fetchone():
        return
    conn.execute('''CREATE TABLE customer_transfer_limits (owner_id TEXT PRIMARY KEY REFERENCES users(id),
        limit_vnd INTEGER NOT NULL CHECK(limit_vnd>=1000),updated_at TEXT NOT NULL)''')
    conn.execute('INSERT INTO schema_migrations VALUES (19,?)', (stamp,))


def read(conn, owner):
    bank = int(conn.execute("SELECT value_json FROM bank_settings WHERE key='transfer_limit_vnd'").fetchone()[0])
    row = conn.execute('SELECT limit_vnd FROM customer_transfer_limits WHERE owner_id=?', (owner,)).fetchone()
    return {'limit_vnd': min(bank, row[0]) if row else bank, 'bank_maximum_vnd': bank}


def validate(conn, user, args):
    if user.role != 'customer':
        raise HTTPException(403, 'ROLE_NOT_PERMITTED')
    amount = LimitArgs.model_validate(args).limit_vnd
    if amount > read(conn, user.id)['bank_maximum_vnd']:
        raise HTTPException(400, 'BANK_TRANSFER_LIMIT')
    return {'limit_vnd': amount}


def apply(conn, user, args, seconds):
    from .identity import audit
    from .action_security import notify
    args = validate(conn, user, args)
    stamp = datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds')
    conn.execute('''INSERT INTO customer_transfer_limits VALUES (?,?,?) ON CONFLICT(owner_id)
        DO UPDATE SET limit_vnd=excluded.limit_vnd,updated_at=excluded.updated_at''', (user.id, args['limit_vnd'], stamp))
    audit(conn, user.id, 'TRANSFER_LIMIT_CHANGED', seconds)
    notify(conn, user.id, 'SECURITY', 'Transfer limit changed', f'Your per-transfer limit is now {args["limit_vnd"]:,} VND.', stamp)
    return {'message': 'Your transfer limit was updated.', 'kind': 'CHANGE_TRANSFER_LIMIT', **args}
