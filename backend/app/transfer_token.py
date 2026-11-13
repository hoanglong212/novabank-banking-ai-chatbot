"""Per-transfer confirmation tokens (B5).

HS256 under TRANSFER_TOKEN_KEY, aud=transfer-confirm. The token names one draft (sub), its owner, recipient and
amount, lives at most five minutes and never past the draft, and its jti is spent when the payment posts.
It binds the confirmation to the exact reviewed parameters and makes it single use. It does not prove identity:
whoever holds the customer's session can obtain one, so a stolen session is limited by the PIN/TOTP step-up and
the transfer limits, not by this token.
"""
from datetime import datetime
import uuid
import jwt
from . import auth
from .posting import TransferError

AUDIENCE = 'transfer-confirm'
BOUND = ('owner_id', 'to_bank', 'to_account', 'amount_vnd')
MAX_SECONDS = 300


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=11').fetchone():
        return
    conn.execute('CREATE TABLE transfer_token_uses (jti TEXT PRIMARY KEY, transfer_id TEXT NOT NULL REFERENCES transfers(id), used_at TEXT NOT NULL)')
    conn.execute('INSERT INTO schema_migrations VALUES (11,?)', (stamp,))


def _seconds(stamp: str) -> int:
    return int(datetime.fromisoformat(stamp).timestamp())


def issue(transfer: dict, draft_expires_at: str, stamp: str) -> str:
    """stamp is the transfer clock (transfers.now), so token and draft expiry can never disagree."""
    now = _seconds(stamp)
    expires = min(now + MAX_SECONDS, _seconds(draft_expires_at))
    claims = {'iss': auth.ISSUER, 'aud': AUDIENCE, 'sub': transfer['id'], 'iat': now, 'exp': expires, 'jti': uuid.uuid4().hex,
              **{k: transfer[k] for k in BOUND}}
    return jwt.encode(claims, auth.TRANSFER_TOKEN_KEY, algorithm='HS256')


def verify(token: str | None, transfer: dict, stamp: str) -> dict:
    """Signature, audience, issuer and expiry, then every bound field against the stored draft."""
    if not token:
        raise TransferError('TOKEN_REQUIRED')
    try:
        # Expiry is checked below against the transfer clock, the same one that expires the draft.
        claims = jwt.decode(token, auth.TRANSFER_TOKEN_KEY, algorithms=['HS256'], audience=AUDIENCE, issuer=auth.ISSUER,
                            options={'require': ['sub', 'iat', 'exp', 'jti', *BOUND], 'verify_exp': False, 'verify_iat': False})
    except jwt.InvalidTokenError:
        raise TransferError('TOKEN_INVALID')
    if not isinstance(claims['exp'], int) or claims['exp'] <= _seconds(stamp):
        raise TransferError('TOKEN_EXPIRED')
    if claims['sub'] != transfer['id'] or any(claims[k] != transfer[k] for k in BOUND):
        raise TransferError('TOKEN_MISMATCH')
    return claims


def spend(conn, claims: dict, transfer_id: str, stamp: str):
    # PRIMARY KEY makes a second spend of the same jti fail even if two confirmations race.
    conn.execute('INSERT INTO transfer_token_uses VALUES (?,?,?)', (claims['jti'], transfer_id, stamp))


def spent(conn, claims: dict) -> bool:
    return conn.execute('SELECT 1 FROM transfer_token_uses WHERE jti=?', (claims['jti'],)).fetchone() is not None
