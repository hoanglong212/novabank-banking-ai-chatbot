"""Public VietQR bank directory; QR generation and settlement remain simulated."""
import asyncio
import base64
import logging
import re
import time
from urllib.parse import urlsplit
import httpx
from .faq import fold

_banks: list[dict] = []  # Kept as an injectable offline catalogue for compatibility tests.
_remote_banks: list[dict] = []
_refresh_after = 0.0
_bank_lock = asyncio.Lock()
API = 'https://api.vietqr.io/v2/banks'
log = logging.getLogger(__name__)
DEMO_BANKS = [
    {'bin': 'NOVA', 'code': 'NVB', 'shortName': 'NovaBank', 'name': 'NovaBank (simulated)', 'logo': ''},
    {'bin': 'DEMOA', 'code': 'DEMOA', 'shortName': 'Demo Bank A', 'name': 'Demo Bank A (simulated)', 'logo': ''},
    {'bin': 'DEMOB', 'code': 'DEMOB', 'shortName': 'Demo Bank B', 'name': 'Demo Bank B (simulated)', 'logo': ''},
]


class VietQRError(Exception):
    def __init__(self, reason_code):
        super().__init__(reason_code)
        self.reason_code = reason_code


async def banks():
    global _remote_banks, _refresh_after
    if _banks:
        return _merge(_banks)
    if time.monotonic() >= _refresh_after:
        async with _bank_lock:
            if time.monotonic() >= _refresh_after:
                try:
                    async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                        response = await client.get(API)
                        response.raise_for_status()
                        body = response.json()
                    if not isinstance(body, dict) or body.get('code') != '00' or not isinstance(body.get('data'), list):
                        raise ValueError('Invalid bank directory')
                    items = []
                    for row in body['data'][:300]:
                        if not isinstance(row, dict) or not re.fullmatch(r'\d{6}', str(row.get('bin', ''))):
                            continue
                        if not all(isinstance(row.get(key), str) and row[key].strip() for key in ('code', 'shortName', 'name')):
                            continue
                        logo = row.get('logo', '')
                        url = urlsplit(logo) if isinstance(logo, str) else None
                        safe_logo = bool(url and url.scheme == 'https' and url.netloc in ('cdn.vietqr.io', 'api.vietqr.io') and url.path.startswith('/img/'))
                        items.append({key: str(row[key])[:200] for key in ('bin', 'code', 'shortName', 'name')} | {'logo': logo if safe_logo else ''})
                    if not items:
                        raise ValueError('Empty bank directory')
                    _remote_banks = list({item['bin']: item for item in items}.values())
                    _refresh_after = time.monotonic() + 24 * 60 * 60
                except (httpx.HTTPError, ValueError, TypeError):
                    # Keep a previously fetched directory and always retain demo banks.
                    _refresh_after = time.monotonic() + 60
                    log.warning('VietQR bank directory unavailable; using cached/demo banks')
    return _merge(_remote_banks)


def _merge(items):
    return [*DEMO_BANKS, *[b for b in items if not any(x['bin'] == b.get('bin') for x in DEMO_BANKS)]]


def find_bank(items, key):
    key = fold(key).replace(' ', '')
    for bank in items:
        if key in (fold(str(bank.get(k, ''))).replace(' ', '') for k in ('bin', 'code', 'shortName')):
            return bank
    return None


def plain(text, limit):
    return ''.join(c for c in fold(text) if c.isalnum() or c == ' ')[:limit].strip()


async def generate(bank, account_no, amount_vnd=None, add_info=None, account_name=None):
    from .local_qr import encode, png
    # Personal demo QR must not wait for, or depend on, the public bank directory.
    found = find_bank(DEMO_BANKS, bank) or find_bank(await banks(), bank)
    if found is None:
        raise VietQRError('UNKNOWN_BANK')
    info, name = plain(add_info or '', 25), plain(account_name or '', 50).upper()
    payload = encode(dict(bank=found['shortName'], account_no=account_no, amount_vnd=amount_vnd,
                          add_info=info, account_name=name))
    image = 'data:image/png;base64,' + base64.b64encode(png(payload)).decode()
    return {'bank': found['shortName'], 'bin': found['bin'], 'account_no': account_no, 'account_name': name,
            'amount_vnd': amount_vnd, 'add_info': info, 'image': image, 'payload': payload,
            'source': 'novabank_internal', 'demo_only': True}
