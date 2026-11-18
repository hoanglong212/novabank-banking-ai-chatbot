"""Document-specific P boundary and audit minimization, not an authorization layer."""
import hashlib
import json
import re
from ..guard import Pseudonymizer, redact_secrets

ALIAS = re.compile(r'<?\b(?:EMAIL|PHONE|NATIONAL_ID|ACCOUNT|NAME)_\d+\b>?', re.I)
LABELED_NAME = re.compile(r'(?im)(?:borrower|full name|name|ho ten|họ tên|ten|tên)\s*:\s*([^\n\r:;]{3,80})')


def prepare(text, vault=None):
    vault = vault or Pseudonymizer()
    text = ALIAS.sub('[source alias removed]', text)
    for match in LABELED_NAME.finditer(text):
        vault._swap('NAME', match.group(1).strip())
    return vault.pseudonymize(redact_secrets(text)[0])


def audit(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    result = {'sha256': hashlib.sha256(encoded.encode()).hexdigest()}
    if isinstance(value, dict):
        identifier = re.compile(r'^[0-9a-f-]{36}$')
        for key in ('document_id', 'id'):
            if isinstance(value.get(key), str) and identifier.fullmatch(value[key]):
                result[key] = value[key]
        for key in ('cited_chunk_ids', 'chunk_ids'):
            if isinstance(value.get(key), list):
                result[key] = [v for v in value[key][:4] if isinstance(v, str) and identifier.fullmatch(v)]
        if type(value.get('found')) is bool:
            result['found'] = value['found']
    return result
