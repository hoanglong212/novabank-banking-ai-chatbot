"""R7/R8: one key per purpose, and a keyed transfer OTP digest."""
import base64
import hashlib
import hmac
import json
import pytest
from fastapi import HTTPException
from app import auth, local_qr, transfers


def test_each_purpose_has_its_own_key():
    keys = [auth.SECRET, auth.QR_KEY, auth.OTP_KEY, auth.TRANSFER_TOKEN_KEY]
    assert len(set(keys)) == 4 and all(len(k) >= 32 for k in keys)


def test_each_key_reads_its_own_environment_variable(monkeypatch):
    for name in ('JWT_SECRET', 'QR_SIGNING_KEY', 'OTP_HASH_KEY', 'TRANSFER_TOKEN_KEY'):
        monkeypatch.setenv(name, 'k-' + name)
        assert auth._key(name) == 'k-' + name


def test_transfer_otp_digest_is_keyed_not_a_plain_hash(monkeypatch):
    plain = hashlib.sha256(b'TRF-1:123456').hexdigest()
    keyed = transfers._otp_hash('TRF-1', '123456')
    assert keyed != plain
    monkeypatch.setattr(auth, 'OTP_KEY', 'another-key-' + 'x' * 40)
    assert transfers._otp_hash('TRF-1', '123456') != keyed  # cannot be recomputed without the key


def test_qr_signed_with_the_jwt_key_is_rejected():
    raw = base64.urlsafe_b64encode(json.dumps({'bank': 'NovaBank', 'account_no': 'ACC-BOB-001'}).encode()).decode().rstrip('=')
    forged = 'NBQR1:' + raw + '.' + hmac.new(auth.SECRET.encode(), ('NBQR1:' + raw).encode(), hashlib.sha256).hexdigest()
    with pytest.raises(HTTPException):
        local_qr.decode(forged)
    assert local_qr.decode(local_qr.encode({'bank': 'NovaBank', 'account_no': 'ACC-BOB-001'}))['account_no'] == 'ACC-BOB-001'
