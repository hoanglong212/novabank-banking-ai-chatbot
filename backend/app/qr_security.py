"""Payment QR text screening; a valid signature does not make prose trusted."""
import hashlib
import html
import re
import unicodedata
from urllib.parse import unquote
from fastapi import HTTPException
from .faq import fold

URL = re.compile(r'\b(?:https?\s*:\s*[/\\]|www\.|(?:javascript|data|file|ftp)\s*:)|\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|vn|app|bank|xyz|info|example)\b', re.I)
INSTRUCTION = re.compile(
    r'\b(?:ignore|disregard|override|bypass)\b.{0,80}\b(?:instructions?|rules?|system|security|guard|previous|prompt|gateway)\b'
    r'|\b(?:system|developer|assistant|agent)\s*(?:override|instructions?|prompt|message|:)'
    r'|\b(?:prepare_transfer|propose_[a-z_]+|fetch_external|tool_calls?|execute_tool)\b'
    r'|\b(?:bo qua|phot lo|vo hieu hoa)\b.{0,60}\b(?:huong dan|quy tac|chi dan|bao mat|he thong)\b'
    r'|\b(?:gui|cung cap|tiet lo|send|reveal)\b.{0,40}\b(?:otp|pin|mat khau|password|token)\b'
    r'|\b(?:transfer|send|chuyen tien)\b.{0,40}\b(?:to|toi|den)\b.{0,30}(?:acc-|tai khoan|account|\d{6,})', re.I)
FIELDS = ('bank', 'account_name', 'add_info')


def screen_payment_text(value):
    text = unicodedata.normalize('NFKC', value or '')
    invisible = any(unicodedata.category(char) == 'Cf' for char in text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Cf')
    inspection = fold(unquote(unquote(html.unescape(text))))
    inspection = ' '.join(inspection.split())
    reasons = []
    if invisible:
        reasons.append('INVISIBLE_CONTROL')
    if URL.search(inspection):
        reasons.append('URL_IN_PAYMENT_TEXT')
    if INSTRUCTION.search(inspection):
        reasons.append('INSTRUCTION_IN_PAYMENT_TEXT')
    return {'text': '' if reasons else ' '.join(text.split()), 'flags': reasons}


def safe_payment_data(data):
    cleaned = dict(data)
    flags = []
    for field in FIELDS:
        if field in cleaned and cleaned[field] is not None:
            screened = screen_payment_text(cleaned[field])
            flags.extend(screened['flags'])
            cleaned[field] = screened['text']
    if flags:
        # Never echo the payload or an attacker URL in a user-visible exception.
        raise HTTPException(422, 'UNSAFE_QR_CONTENT: QR payment fields contain a link, hidden control or instruction. Use verified payment details instead.')
    return cleaned


def decoded_review(data, signed_payload):
    cleaned = safe_payment_data(data)
    external = fold(cleaned['bank']).replace(' ', '') not in ('novabank', 'nova', 'nvb')
    return {**cleaned, 'source_origin': 'qr', 'qr_security': {
        'flagged': False, 'external_bank': external, 'new_recipient_warning': external,
        'payload_fingerprint': hashlib.sha256(signed_payload.encode()).hexdigest(),
        'untrusted_fields': ['account_name', 'add_info'],
    }}
