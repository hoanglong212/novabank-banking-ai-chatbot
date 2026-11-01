"""Password login issuing short-lived HS256 JWTs for the fictional demo customers.

Local demo identity: MFA, persisted sessions and credential-version checks.
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
# Without JWT_SECRET, restart invalidates access JWTs and pending email codes; refresh sessions persist.
SECRET = setting('JWT_SECRET') or secrets.token_urlsafe(48)
TTL_SECONDS = 300


@dataclass(frozen=True)
class DemoPrincipal:
    id: str
    name: str
    password_hash: str
    accounts: tuple[str, ...]
    role: str = 'customer'
    auth_version: int = 0
    session_id: str | None = None

    @property
    def permissions(self) -> frozenset[str]:
        return ROLE_PERMISSIONS.get(self.role, frozenset())


ROLE_PERMISSIONS = {
    'customer': frozenset({'banking:own', 'notifications:own'}),
    'support': frozenset({'support:read', 'support:write', 'notifications:own'}),
    'operations': frozenset({'admin:transactions:read', 'admin:audit:read', 'notifications:own'}),
    'auditor': frozenset({'admin:transactions:read', 'admin:audit:read', 'notifications:own'}),
    'admin': frozenset({'admin:transactions:read', 'admin:audit:read', 'notifications:own', 'settings:write', 'support:read', 'support:write'}),
}


# Demo passwords (documented in README): alice / Alice@2026, bob / Bob@2026.
DEMO_USERS = (
    DemoPrincipal('alice', 'Alice', 'pbkdf2_sha256$310000$df30858ca0a57461471ecf59253bcf4f$'
                  '9f0b98090c696d01a150831f1e7eb5e6124445d188df3f366b3b28d557d23642', ('ACC-ALICE-001',)),
    DemoPrincipal('bob', 'Bob', 'pbkdf2_sha256$310000$b767d655fff701ab12743b6e89419b53$'
                  '138ff19ece34fd3a67d9fdd7ea2c9a4ef926929a9fbf92885de1dfb3a0f21e0e', ('ACC-BOB-001',)),
    DemoPrincipal('charlie', 'Charlie', 'pbkdf2_sha256$310000$9d2fc444215c489369654ce4eaa854c0$'
                  'ead6cabe2d1bf6d0835d93ca862c925ea9517e0aa6ee5e86024b3d25a492a7e5', ('ACC-CHARLIE-001',)),
    DemoPrincipal('support', 'Support', 'pbkdf2_sha256$310000$a5f58dc0d6833eea0d7a3c37a9fe836e$'
                  '6a941dd799a7beb37b3fda44fbd61d023ed561a61734b386d5ec1f424cda9357', (), 'support'),
    DemoPrincipal('operations', 'Operations', 'pbkdf2_sha256$310000$ee17fae8aa3f716a9bbd7dcd1cf5a09f$'
                  '59f88f5e3e2abc416b0c858d612a237824878d9447dbab897a047be2cadf26d8', (), 'operations'),
    DemoPrincipal('auditor', 'Auditor', 'pbkdf2_sha256$310000$050f5abffb4f4a5fac793bd58587eaf9$'
                  'e5c83597d62e5ae5c07de42d6c312ca97d9650cbcfc84d43edfb306c0b5b859b', (), 'auditor'),
    DemoPrincipal('admin', 'Admin', 'pbkdf2_sha256$310000$77d4b7482138746db098c148911a9b5a$'
                  '8e36402360d6f314b2e6aba4d2d98248c8db0102ed30805f9f4ab7be4ae24020', (), 'admin'),
)
USERS = {u.id: u for u in DEMO_USERS}
# Perform password work for unknown usernames too; this is not a constant-time HTTP guarantee.
DUMMY_HASH = DEMO_USERS[0].password_hash


def verify_password(password: str, stored: str) -> bool:
    _, iterations, salt, expected = stored.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)


def issue_token(user: DemoPrincipal) -> str:
    now = int(time.time())
    return jwt.encode({'sub': user.id, 'name': user.name, 'iss': ISSUER, 'iat': now, 'exp': now + TTL_SECONDS,
                       'ver': user.auth_version, 'sid': user.session_id},
                      SECRET, algorithm='HS256')


def authenticate(authorization: str | None) -> DemoPrincipal:
    from .dependencies import get_db
    from .identity import lookup_principal
    from . import session_security as security
    from dataclasses import replace
    from contextlib import closing
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Please sign in')
    try:
        claims = jwt.decode(authorization[7:], SECRET, algorithms=['HS256'], issuer=ISSUER,
                            options={'require': ['sub', 'exp', 'iat', 'iss', 'sid', 'ver']})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session expired. Please sign in again.')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session. Please sign in again.')
    user = lookup_principal(get_db(), claims['sub'])
    if user is None or type(claims['ver']) is not int or claims['ver'] != user.auth_version or not isinstance(claims['sid'], str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session. Please sign in again.')
    with closing(get_db().connect()) as conn:
        security.active_session(conn, claims['sid'], user.id, user.auth_version, security.timestamp())
    return replace(user, session_id=claims['sid'])
