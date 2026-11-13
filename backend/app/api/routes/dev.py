"""Explicit demo-only simulated mailbox. Never enabled by default.

Signed-in users read only their own mail. Before sign-in, a sign-in code is readable only with the
challenge_id the login form holds. Verification and reset links have no session or challenge to bind
to, so they are never served over HTTP: read them with scripts/dev-outbox.py on the server machine.
"""
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from ...config import setting
from ...dependencies import get_db, current_user
from ...identity import digest
from ...identity_schemas import IdentityInput

router = APIRouter(prefix='/api/dev', dependencies=[])


def demo_only():
    if setting('ENV') != 'demo':
        raise HTTPException(404, 'Not found')


class ChallengeInput(IdentityInput):
    challenge_id: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')


def masked(recipient):
    return recipient[:1] + '***@***' if '@' in recipient else '***'


def view(row):
    valid = row['expires_at'] is not None and row['expires_at'] > int(time.time())
    # Relative local fragment only. Never trust Host to construct action links.
    action = row['action_path'] or ''
    safe_action = action.startswith(('/#verify-email?', '/#reset-password?'))
    return {'id': row['id'], 'recipient': masked(row['recipient']), 'kind': row['kind'],
            'created_at': row['created_at'], 'expires_at': row['expires_at'],
            'message': row['body'] or 'Simulated NovaBank email.',
            'code': row['secret_text'] if valid else None,
            'action_url': action if valid and safe_action else None}


@router.get('/outbox', dependencies=[Depends(demo_only)])
def inbox(user=Depends(current_user), db=Depends(get_db)):
    with db.connect() as conn:
        rows = conn.execute('SELECT id,recipient,kind,created_at,expires_at FROM dev_outbox WHERE user_id=? ORDER BY rowid DESC LIMIT 50',
                            (user.id,))
        return {'items': [{**dict(r), 'recipient': masked(r['recipient'])} for r in rows]}


# POST keeps the challenge out of URLs and access logs. No rate limit: the challenge is 256 random bits,
# lives five minutes, and the inbox page polls it.
@router.post('/outbox/challenge', dependencies=[Depends(demo_only)])
def challenge_mail(payload: ChallengeInput, db=Depends(get_db)):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM dev_outbox WHERE challenge_id=? AND kind='LOGIN_OTP' ORDER BY rowid DESC LIMIT 1",
                           (digest(payload.challenge_id),)).fetchone()
        if row is None:
            raise HTTPException(404, 'Message not found')
        return view(row)


@router.get('/outbox/{message_id}', dependencies=[Depends(demo_only)])
def message(message_id: str, user=Depends(current_user), db=Depends(get_db)):
    with db.connect() as conn:
        row = conn.execute('SELECT * FROM dev_outbox WHERE id=? AND user_id=?', (message_id, user.id)).fetchone()
        if row is None:
            raise HTTPException(404, 'Message not found')
        return view(row)
