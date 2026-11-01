from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import Field
from . import mfa, mfa_settings, sessions, session_security as security
from .dependencies import get_db, current_user
from .identity import request_limit
from .identity_schemas import IdentityInput
from .schemas import LoginRequest


class ChallengeInput(IdentityInput):
    challenge_id: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')


class CodeInput(IdentityInput):
    code: str = Field(min_length=6, max_length=6, pattern=r'^[0-9]{6}$')


class VerifyInput(ChallengeInput, CodeInput):
    pass


class PasswordCheck(IdentityInput):
    password: str = Field(min_length=1, max_length=128)


class RefreshInput(IdentityInput):
    refresh_token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')


def no_cache(response: Response):
    response.headers['Cache-Control'] = 'no-store'


def limited(request: Request, db=Depends(get_db)):
    request_limit(db, request.url.path, request.client.host if request.client else 'unknown')


router = APIRouter(prefix='/api/auth', dependencies=[Depends(no_cache)])


@router.post('/login', status_code=202, dependencies=[Depends(limited)])
def login(payload: LoginRequest, request: Request, db=Depends(get_db)):
    return mfa.begin_login(db, payload.username, payload.password, *security.metadata(request))


@router.post('/mfa/verify', dependencies=[Depends(limited)])
def verify(payload: VerifyInput, db=Depends(get_db)):
    return mfa.complete(db, payload.challenge_id, payload.code)


@router.post('/mfa/email', status_code=202, dependencies=[Depends(limited)])
def resend(payload: ChallengeInput, db=Depends(get_db)):
    return mfa.resend(db, payload.challenge_id)


@router.post('/refresh', dependencies=[Depends(limited)])
def refresh(payload: RefreshInput, db=Depends(get_db)):
    return sessions.rotate(db, payload.refresh_token)


@router.get('/sessions')
def list_sessions(user=Depends(current_user), db=Depends(get_db)):
    return sessions.list_sessions(db, user)


@router.delete('/sessions/{session_id}')
def revoke(session_id: str, user=Depends(current_user), db=Depends(get_db)):
    return sessions.revoke_owned(db, user, session_id)


@router.post('/logout')
def logout(user=Depends(current_user), db=Depends(get_db)):
    return sessions.revoke_owned(db, user, user.session_id)


@router.post('/activity')
def activity(user=Depends(current_user), db=Depends(get_db)):
    return sessions.activity(db, user)


@router.get('/login-history')
def history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), user=Depends(current_user), db=Depends(get_db)):
    return sessions.login_history(db, user, limit, offset)


@router.get('/mfa')
def mfa_status(user=Depends(current_user), db=Depends(get_db)):
    return mfa_settings.status(db, user)


@router.post('/mfa/setup', dependencies=[Depends(limited)])
def setup(payload: PasswordCheck, user=Depends(current_user), db=Depends(get_db)):
    return mfa_settings.setup(db, user, payload.password)


@router.post('/mfa/enable', dependencies=[Depends(limited)])
def enable(payload: CodeInput, user=Depends(current_user), db=Depends(get_db)):
    return mfa_settings.enable(db, user, payload.code)


@router.post('/mfa/disable-request', dependencies=[Depends(limited)])
def disable_request(payload: PasswordCheck, user=Depends(current_user), db=Depends(get_db)):
    return mfa_settings.disable_request(db, user, payload.password)


@router.post('/mfa/disable', dependencies=[Depends(limited)])
def disable(payload: VerifyInput, user=Depends(current_user), db=Depends(get_db)):
    return mfa.complete(db, payload.challenge_id, payload.code, 'DISABLE_TOTP', user)
