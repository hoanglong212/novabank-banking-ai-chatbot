"""Explicit demo-only simulated mailbox. Never enabled by default.

Signed-in users read only their own mail. Before sign-in, a sign-in code is readable only with the
challenge_id the login form holds. Verification and reset links have no session or challenge to bind
to, so they are never served over HTTP: read them with scripts/dev-outbox.py on the server machine.
"""
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from ...config import setting
from ...dependencies import get_db, current_user
from ...identity import digest, quota, timestamp, transaction
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


# One inbox tab polls every 3 s for at most the challenge's 5 minutes (100 requests); this leaves room for
# several sign-ins from one address (all requests share 127.0.0.1 behind the Vite proxy) while capping floods.
CHALLENGE_POLLS = 600


def challenge_limit(request: Request, db=Depends(get_db)):
    peer = request.client.host if request.client else 'unknown'
    with transaction(db) as conn:
        allowed = quota(conn, 'outbox-challenge', peer, CHALLENGE_POLLS, 900, timestamp())
    if not allowed:
        raise HTTPException(429, 'Too many inbox requests. Please try again in 15 minutes.', headers={'Retry-After': '900'})


# POST keeps the challenge out of URLs and access logs. demo_only runs first, so outside ENV=demo nothing is counted.
@router.post('/outbox/challenge', dependencies=[Depends(demo_only), Depends(challenge_limit)])
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
