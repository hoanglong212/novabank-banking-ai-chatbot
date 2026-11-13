"""Explicit demo-only simulated mailbox. Never enabled by default."""
import time
from fastapi import APIRouter, Depends, HTTPException
from ...config import setting
from ...dependencies import get_db

router = APIRouter(prefix='/api/dev', dependencies=[])


def demo_only():
    if setting('ENV') != 'demo':
        raise HTTPException(404, 'Not found')


def masked(recipient):
    return recipient[:1] + '***@***' if '@' in recipient else '***'


@router.get('/outbox', dependencies=[Depends(demo_only)])
def inbox(db=Depends(get_db)):
    with db.connect() as conn:
        rows = conn.execute('SELECT id,recipient,kind,created_at,expires_at FROM dev_outbox ORDER BY rowid DESC LIMIT 50')
        return {'items': [{**dict(r), 'recipient': masked(r['recipient'])} for r in rows]}


@router.get('/outbox/{message_id}', dependencies=[Depends(demo_only)])
def message(message_id: str, db=Depends(get_db)):
    with db.connect() as conn:
        row = conn.execute('SELECT * FROM dev_outbox WHERE id=?', (message_id,)).fetchone()
        if row is None:
            raise HTTPException(404, 'Message not found')
        valid = row['expires_at'] is not None and row['expires_at'] > int(time.time())
        # Relative local fragment only. Never trust Host to construct action links.
        action = row['action_path'] or ''
        safe_action = action.startswith(('/#verify-email?', '/#reset-password?'))
        return {'id': row['id'], 'recipient': masked(row['recipient']), 'kind': row['kind'],
                'created_at': row['created_at'], 'expires_at': row['expires_at'],
                'message': row['body'] or 'Simulated NovaBank email.',
                'code': row['secret_text'] if valid else None,
                'action_url': action if valid and safe_action else None}
