"""Intentionally insecure local identity switch. NEVER use in production."""
from dataclasses import dataclass
from fastapi import HTTPException, status


@dataclass(frozen=True)
class DemoPrincipal:
    id: str
    name: str
    token: str
    accounts: tuple[str, ...]


DEMO_USERS = (
    DemoPrincipal('alice', 'Minh Anh', 'demo-alice-token', ('ACC-ALICE-001',)),
    DemoPrincipal('bob', 'Gia Bảo', 'demo-bob-token', ('ACC-BOB-001',)),
)


def authenticate(authorization: str | None) -> DemoPrincipal:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing demo access token')
    token = authorization[7:]
    for user in DEMO_USERS:
        if user.token == token:
            return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid demo access token')
