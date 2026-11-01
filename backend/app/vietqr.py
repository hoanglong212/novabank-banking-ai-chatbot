"""Compatibility facade for the private NovaBank demo QR and bank simulator.

Historical tool/API names remain for saved conversations. No network or NAPAS
payload is generated; new UI calls these NovaBank demo QR codes.
"""
import base64
from .faq import fold

_banks: list[dict] = []  # Kept as an injectable offline catalogue for compatibility tests.
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
    return [*_banks, *[b for b in DEMO_BANKS if not any(x.get('bin') == b['bin'] for x in _banks)]]


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
    found = find_bank(await banks(), bank)
    if found is None:
        raise VietQRError('UNKNOWN_BANK')
    info, name = plain(add_info or '', 25), plain(account_name or '', 50).upper()
    payload = encode(dict(bank=found['shortName'], account_no=account_no, amount_vnd=amount_vnd,
                          add_info=info, account_name=name))
    image = 'data:image/png;base64,' + base64.b64encode(png(payload)).decode()
    return {'bank': found['shortName'], 'bin': found['bin'], 'account_no': account_no, 'account_name': name,
            'amount_vnd': amount_vnd, 'add_info': info, 'image': image, 'payload': payload,
            'source': 'novabank_internal', 'demo_only': True}
