import base64
import binascii
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from .dependencies import customer_user
from .identity_schemas import IdentityInput
from .local_qr import decode, uploaded_png

router = APIRouter(prefix='/api/qr', dependencies=[Depends(customer_user)])


class ScanInput(IdentityInput):
    payload: str | None = Field(default=None, max_length=4000)
    image_base64: str | None = Field(default=None, max_length=2800000)


@router.post('/decode')
def scan(payload: ScanInput):
    if payload.payload and not payload.image_base64:
        return decode(payload.payload)
    if payload.image_base64 and not payload.payload:
        try:
            data = base64.b64decode(payload.image_base64, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, 'Invalid image encoding.')
        return uploaded_png(data)
    raise HTTPException(422, 'Provide either QR text or one original NovaBank PNG.')
