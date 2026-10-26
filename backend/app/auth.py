"""Password login issuing short-lived HS256 JWTs for the fictional demo customers.

Not a production identity provider: users are fixed, there is no MFA, refresh token or revocation list.
"""
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
import jwt
from fastapi import HTTPException, status
from .config import setting

ISSUER = 'novabank-demo'
# shortcut: without JWT_SECRET every restart signs with a new key and logs everyone out; set it in .env.
SECRET = setting('JWT_SECRET') or secrets.token_urlsafe(48)
TTL_SECONDS = int(setting('JWT_TTL_MINUTES', '60')) * 60
MAX_FAILURES, FAILURE_WINDOW = 5, 300


@dataclass(frozen=True)
class DemoPrincipal:
    id: str
    name: str
    password_hash: str
    accounts: tuple[str, ...]


# Demo passwords (documented in README): alice / Alice@2026, bob / Bob@2026.
DEMO_USERS = (
    DemoPrincipal('alice', 'Alice', 'pbkdf2_sha256$310000$df30858ca0a57461471ecf59253bcf4f$'
                  '9f0b98090c696d01a150831f1e7eb5e6124445d188df3f366b3b28d557d23642', ('ACC-ALICE-001',)),
    DemoPrincipal('bob', 'Bob', 'pbkdf2_sha256$310000$b767d655fff701ab12743b6e89419b53$'
                  '138ff19ece34fd3a67d9fdd7ea2c9a4ef926929a9fbf92885de1dfb3a0f21e0e', ('ACC-BOB-001',)),
)
USERS = {u.id: u for u in DEMO_USERS}
# Verified when the username is unknown, so response time does not reveal which usernames exist.
DUMMY_HASH = DEMO_USERS[0].password_hash
_failures: dict[str, list[float]] = {}


def verify_password(password: str, stored: str) -> bool:
    _, iterations, salt, expected = stored.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)


def login(username: str, password: str) -> DemoPrincipal:
    key = username.strip().lower()
    now = time.monotonic()
    # shortcut: in-memory, per process; use a shared store (e.g. Redis) behind several workers.
    recent = [t for t in _failures.get(key, []) if now - t < FAILURE_WINDOW]
    if len(recent) >= MAX_FAILURES:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many failed attempts. Try again in 5 minutes.')
    user = USERS.get(key)
    if not verify_password(password, user.password_hash if user else DUMMY_HASH) or user is None:
        _failures[key] = [*recent, now]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')
    _failures.pop(key, None)
    return user


def issue_token(user: DemoPrincipal) -> str:
    now = int(time.time())
    return jwt.encode({'sub': user.id, 'name': user.name, 'iss': ISSUER, 'iat': now, 'exp': now + TTL_SECONDS},
                      SECRET, algorithm='HS256')


def authenticate(authorization: str | None) -> DemoPrincipal:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Please sign in')
    try:
        claims = jwt.decode(authorization[7:], SECRET, algorithms=['HS256'], issuer=ISSUER,
                            options={'require': ['sub', 'exp', 'iat', 'iss']})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session expired. Please sign in again.')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session. Please sign in again.')
    user = USERS.get(claims['sub'])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session. Please sign in again.')
    return user
