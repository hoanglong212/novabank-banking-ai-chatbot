"""Document-specific P boundary and audit minimization, not an authorization layer."""
import hashlib
import json
import re
from ..guard import Pseudonymizer, redact_secrets, BARE_TOKEN
from .binding import MAX_SUMMARY_PASSAGES

ALIAS = re.compile(r'<?\b(?:EMAIL|PHONE|NATIONAL_ID|ACCOUNT|NAME)_\d+\b>?', re.I)
LABELED_NAME = re.compile(r'(?im)(?:borrower|full name|name|ho ten|họ tên|ten|tên)\s*:\s*([^\n\r:;]{3,80})')


def prepare(text, vault=None):
    vault = vault or Pseudonymizer()
    text = ALIAS.sub('[source alias removed]', text)
    for match in LABELED_NAME.finditer(text):
        vault._swap('NAME', match.group(1).strip())
    return vault.pseudonymize(redact_secrets(text)[0])


def register(texts, vault=None):
    """Discover document-wide identities before any chunk reaches any model."""
    vault = vault or Pseudonymizer()
    clean = [ALIAS.sub('[source alias removed]', text) for text in texts]
    for text in clean:
        for match in LABELED_NAME.finditer(text):
            vault._swap('NAME', match.group(1).strip())
    # Presidio registers labeled short accounts as well as standalone identifiers.
    # A second pass by the caller then protects even earlier/unlabeled occurrences.
    for text in clean:
        vault.pseudonymize(redact_secrets(text)[0])
    return vault


def aliases(text):
    return set(BARE_TOKEN.findall(text))


def exposed(conn, run):
    return bool(conn.execute("""SELECT 1 FROM agent_calls c JOIN agent_runs r ON r.id=c.run_id
        WHERE r.conversation_id=? AND r.owner_id=? AND c.name='ask_document' LIMIT 1""",
        (run['conversation_id'], run['owner_id'])).fetchone())


def audit_result(value, key=''):
    """Keep typed bank facts needed by output checks; hash all free-form prose."""
    if isinstance(value, dict):
        return {k: audit_result(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [audit_result(v, key) for v in value]
    if not isinstance(value, str):
        return value
    identifiers = {'id','document_id','account_id','from_account','to_account','transaction_id','approval_id'}
    enums = {'status','kind','scope','currency','type','direction'}
    if key in identifiers and (re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value) or re.fullmatch(r'<(?:ACCOUNT|NAME|EMAIL|PHONE|NATIONAL_ID)_\d+>', value)):
        return value
    if key in enums and re.fullmatch(r'[A-Za-z_]{1,40}', value):
        return value
    if key in {'date','created_at','completed_at','matures_at','opened_at'} and re.fullmatch(r'[0-9T:+.Z-]{8,40}', value):
        return value
    return '[text sha256:' + hashlib.sha256(value.encode()).hexdigest() + ']'


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
                result[key] = [v for v in value[key][:MAX_SUMMARY_PASSAGES] if isinstance(v, str) and identifier.fullmatch(v)]
        if type(value.get('found')) is bool:
            result['found'] = value['found']
    return result
