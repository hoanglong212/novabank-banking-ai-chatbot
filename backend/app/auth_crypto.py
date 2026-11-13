"""RFC 6238 TOTP and encrypted local seed storage; no custom encryption."""
import base64
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import struct
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from .config import setting


def new_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode()


def totp(secret, step, digits=6):
    key = base64.b32decode(secret, casefold=True)
    mac = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = mac[-1] & 15
    number = (struct.unpack('>I', mac[offset:offset + 4])[0] & 0x7fffffff) % (10 ** digits)
    return str(number).zfill(digits)


def match_totp(secret, code, stamp, last_step=-1):
    for step in (stamp // 30, stamp // 30 - 1, stamp // 30 + 1):
        if step > last_step and step >= 0 and hmac.compare_digest(totp(secret, step), code):
            return step
    return None


def cipher(db, create=False):
    try:
        key = setting('MFA_ENCRYPTION_KEY').encode()
        if not key:
            path = Path(str(Path(db.path).resolve()) + '.mfa.key')
            if create and not path.exists():
                # Called under the DB write lock, serializing first-time setup across workers.
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'wb') as target:
                    target.write(Fernet.generate_key())
            key = path.read_bytes()
        return Fernet(key)
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Authenticator key is unavailable. Use the email fallback and contact the demo operator.') from exc


def encrypt_secret(db, value):
    return cipher(db, create=True).encrypt(value.encode()).decode()


def decrypt_secret(db, value):
    try:
        return cipher(db).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(503, 'Authenticator key is unavailable. Use the email fallback and contact the demo operator.') from exc


def otp_digest(challenge_hash, code):
    from .auth import OTP_KEY
    return hmac.new(OTP_KEY.encode(), (challenge_hash + ':' + code).encode(), hashlib.sha256).hexdigest()
