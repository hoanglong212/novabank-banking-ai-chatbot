"""Server-owned identity, database and permission dependencies shared by routers."""
from fastapi import Depends, Header, HTTPException
from .auth import DemoPrincipal, authenticate
from .config import setting
from .database import Database


def get_db() -> Database:
    return Database(setting('DB_PATH', './novabank_demo.sqlite3'))


def current_user(authorization: str | None = Header(default=None)) -> DemoPrincipal:
    return authenticate(authorization)


def require_permission(permission: str):
    def allowed(user: DemoPrincipal = Depends(current_user)) -> DemoPrincipal:
        if permission not in user.permissions:
            raise HTTPException(status_code=403, detail='Permission denied')
        return user
    return allowed


customer_user = require_permission('banking:own')


def assistant_user(user: DemoPrincipal = Depends(current_user)) -> DemoPrincipal:
    if user.role not in ('customer', 'support', 'operations', 'auditor', 'admin'):
        raise HTTPException(403, 'ROLE_NOT_PERMITTED')
    return user
