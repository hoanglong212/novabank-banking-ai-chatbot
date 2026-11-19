from fastapi import APIRouter, Depends, Request, Response
from . import identity
from .dependencies import get_db
from .identity_schemas import EmailInput, RegisterInput, ResetInput, TokenInput


def no_cache(response: Response):
    response.headers['Cache-Control'] = 'no-store'


router = APIRouter(prefix='/api/auth', dependencies=[Depends(no_cache)])


@router.post('/register', status_code=202)
def register(payload: RegisterInput, request: Request, db=Depends(get_db)):
    identity.request_limit(db, request)
    return identity.register(db, payload)


@router.post('/resend-verification', status_code=202)
def resend(payload: EmailInput, request: Request, db=Depends(get_db)):
    identity.request_limit(db, request)
    return identity.send_instructions(db, payload.email, 'VERIFY_EMAIL')


@router.post('/verify-email')
def verify(payload: TokenInput, request: Request, db=Depends(get_db)):
    identity.request_limit(db, request)
    return identity.verify_email(db, payload.token)


@router.post('/forgot-password', status_code=202)
def forgot(payload: EmailInput, request: Request, db=Depends(get_db)):
    identity.request_limit(db, request)
    return identity.send_instructions(db, payload.email, 'RESET_PASSWORD')


@router.post('/reset-password')
def reset(payload: ResetInput, request: Request, db=Depends(get_db)):
    identity.request_limit(db, request)
    return identity.reset_password(db, payload.token, payload.password)
