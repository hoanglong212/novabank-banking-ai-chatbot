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


class PinInput(IdentityInput):
    password: str = Field(min_length=1, max_length=128)
    pin: str = Field(min_length=6, max_length=6, pattern=r'^[0-9]{6}$')


class RefreshInput(IdentityInput):
    refresh_token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')


def no_cache(response: Response):
    response.headers['Cache-Control'] = 'no-store'


router = APIRouter(prefix='/api/auth', dependencies=[Depends(no_cache)])


@router.post('/login', status_code=202)
def login(payload: LoginRequest, request: Request, db=Depends(get_db)):
    request_limit(db, request)
    return mfa.begin_login(db, payload.username, payload.password, *security.metadata(request), payload.device_token)


@router.post('/mfa/verify')
def verify(payload: VerifyInput, request: Request, db=Depends(get_db)):
    request_limit(db, request)
    return mfa.complete(db, payload.challenge_id, payload.code)


@router.post('/mfa/email', status_code=202)
def resend(payload: ChallengeInput, request: Request, db=Depends(get_db)):
    request_limit(db, request)
    return mfa.resend(db, payload.challenge_id)


@router.post('/refresh')
def refresh(payload: RefreshInput, request: Request, db=Depends(get_db)):
    request_limit(db, request)
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


@router.post('/pin')
def transaction_pin(payload: PinInput, user=Depends(current_user), db=Depends(get_db)):
    # Password check inside counts failures toward the account lockout.
    return mfa_settings.set_pin(db, user, payload.password, payload.pin)


@router.post('/mfa/setup')
def setup(payload: PasswordCheck, request: Request, user=Depends(current_user), db=Depends(get_db)):
    request_limit(db, request)
    return mfa_settings.setup(db, user, payload.password)


@router.post('/mfa/enable')
def enable(payload: CodeInput, request: Request, user=Depends(current_user), db=Depends(get_db)):
    request_limit(db, request)
    return mfa_settings.enable(db, user, payload.code)


@router.post('/mfa/disable-request')
def disable_request(payload: PasswordCheck, request: Request, user=Depends(current_user), db=Depends(get_db)):
    request_limit(db, request)
    return mfa_settings.disable_request(db, user, payload.password)


@router.post('/mfa/disable')
def disable(payload: VerifyInput, request: Request, user=Depends(current_user), db=Depends(get_db)):
    request_limit(db, request)
    return mfa.complete(db, payload.challenge_id, payload.code, 'DISABLE_TOTP', user)
