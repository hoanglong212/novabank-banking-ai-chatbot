"""VietQR client (https://www.vietqr.io). Called only by ToolDispatcher after authorization.

With VIETQR_CLIENT_ID/VIETQR_API_KEY set, /v2/generate returns the QR image; otherwise the
public Quick Link image service renders the same NAPAS payload without credentials.
"""
from urllib.parse import urlencode
import httpx
from .config import setting
from .faq import fold

API = 'https://api.vietqr.io/v2'
_banks: list[dict] = []


class VietQRError(Exception):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


async def banks() -> list[dict]:
    global _banks
    if not _banks:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(API + '/banks')
                response.raise_for_status()
                _banks = response.json()['data']
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise VietQRError('VIETQR_UNAVAILABLE') from exc
    return _banks


def find_bank(items: list[dict], key: str) -> dict | None:
    key = fold(key).replace(' ', '')
    for bank in items:
        names = (bank.get('bin', ''), bank.get('code', ''), bank.get('shortName', ''))
        if key in (fold(str(n)).replace(' ', '') for n in names):
            return bank
    return None


def plain(text: str, limit: int) -> str:
    # NAPAS fields accept ASCII only.
    return ''.join(c for c in fold(text) if c.isalnum() or c == ' ')[:limit].strip()


async def generate(bank: str, account_no: str, amount_vnd: int | None = None,
                   add_info: str | None = None, account_name: str | None = None) -> dict:
    found = find_bank(await banks(), bank)
    if found is None:
        raise VietQRError('UNKNOWN_BANK')
    info = plain(add_info or '', 25)
    name = plain(account_name or '', 50).upper()
    client_id, api_key = setting('VIETQR_CLIENT_ID'), setting('VIETQR_API_KEY')
    if client_id and api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(API + '/generate', headers={'x-client-id': client_id, 'x-api-key': api_key}, json={
                    'accountNo': account_no, 'accountName': name, 'acqId': int(found['bin']),
                    'amount': amount_vnd or 0, 'addInfo': info, 'format': 'text', 'template': 'compact'})
                response.raise_for_status()
                body = response.json()
                if body.get('code') != '00':
                    raise VietQRError('VIETQR_REJECTED')
                image, source = body['data']['qrDataURL'], 'vietqr_api'
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise VietQRError('VIETQR_UNAVAILABLE') from exc
    else:
        query = {k: v for k, v in (('amount', amount_vnd), ('addInfo', info), ('accountName', name)) if v}
        image = f'https://img.vietqr.io/image/{found["bin"]}-{account_no}-compact.png' + (f'?{urlencode(query)}' if query else '')
        source = 'vietqr_quicklink'
    return {'bank': found['shortName'], 'bin': found['bin'], 'account_no': account_no, 'account_name': name,
            'amount_vnd': amount_vnd, 'add_info': info, 'image': image, 'source': source}
