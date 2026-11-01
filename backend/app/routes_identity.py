from fastapi import APIRouter, Depends, Request, Response
from . import identity
from .dependencies import get_db
from .identity_schemas import EmailInput, RegisterInput, ResetInput, TokenInput


def public_request(request: Request, response: Response, db=Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    identity.request_limit(db, request.url.path, request.client.host if request.client else 'unknown')


router = APIRouter(prefix='/api/auth', dependencies=[Depends(public_request)])


@router.post('/register', status_code=202)
def register(payload: RegisterInput, db=Depends(get_db)):
    return identity.register(db, payload)


@router.post('/resend-verification', status_code=202)
def resend(payload: EmailInput, db=Depends(get_db)):
    return identity.send_instructions(db, payload.email, 'VERIFY_EMAIL')


@router.post('/verify-email')
def verify(payload: TokenInput, db=Depends(get_db)):
    return identity.verify_email(db, payload.token)


@router.post('/forgot-password', status_code=202)
def forgot(payload: EmailInput, db=Depends(get_db)):
    return identity.send_instructions(db, payload.email, 'RESET_PASSWORD')


@router.post('/reset-password')
def reset(payload: ResetInput, db=Depends(get_db)):
    return identity.reset_password(db, payload.token, payload.password)
