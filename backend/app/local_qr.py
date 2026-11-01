"""Private NovaBank QR format. Not NAPAS/EMV and never payable at a real bank."""
import base64
import hashlib
import hmac
import json
from io import BytesIO
from PIL import Image, ImageDraw, PngImagePlugin
from reportlab.graphics.barcode import qrencoder
from fastapi import HTTPException
from .auth import SECRET


def encode(payload):
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':'), ensure_ascii=True).encode()).decode().rstrip('=')
    signature = hmac.new(SECRET.encode(), ('NBQR1:' + raw).encode(), hashlib.sha256).hexdigest()
    return 'NBQR1:' + raw + '.' + signature


def decode(value):
    if len(value) > 4000 or not value.startswith('NBQR1:'):
        raise HTTPException(422, 'Use a NovaBank demo QR code.')
    try:
        raw, signature = value[6:].rsplit('.', 1)
        expected = hmac.new(SECRET.encode(), ('NBQR1:' + raw).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError('Invalid signature')
        data = json.loads(base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)))
        from .schemas import VietQRArgs
        return VietQRArgs(**data).model_dump(exclude_none=True)
    except (ValueError, TypeError, KeyError):
        raise HTTPException(422, 'The demo QR code is invalid or was signed by a different server.')


def png(value):
    qr = qrencoder.QRCode(None, 1)
    qr.addData(value)
    qr.make()
    n = qr.getModuleCount(); scale = 6; border = 4
    img = Image.new('RGB', ((n + border * 2) * scale,) * 2, 'white')
    draw = ImageDraw.Draw(img)
    for y in range(n):
        for x in range(n):
            if qr.isDark(y, x):
                left, top = (x + border) * scale, (y + border) * scale
                draw.rectangle((left, top, left + scale - 1, top + scale - 1), fill='black')
    info = PngImagePlugin.PngInfo(); info.add_text('NovaBankPayload', value)
    out = BytesIO(); img.save(out, format='PNG', pnginfo=info)
    return out.getvalue()


def uploaded_png(raw):
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(422, 'QR image must be at most 2 MB.')
    try:
        with Image.open(BytesIO(raw)) as img:
            if img.format != 'PNG' or img.width * img.height > 4_000_000:
                raise ValueError('Unsupported image')
            value = img.info.get('NovaBankPayload')
            if not isinstance(value, str):
                raise ValueError('Missing payload')
    except (OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, 'Upload the original NovaBank PNG, or paste its QR text. Cropped images need a browser QR reader.')
    return decode(value)
