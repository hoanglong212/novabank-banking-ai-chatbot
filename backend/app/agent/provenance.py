"""Monotone source labels; model-readable text never grants action authority."""
import json
import hashlib
import re
from fastapi import HTTPException
from ..security_events import emit

FIELD_TRUST = {
    'get_recent_transactions': ('description', 'counterparty_name'),
    'get_transaction_status': ('description', 'counterparty_name'),
    'get_accounts': ('nickname',), 'get_beneficiaries': ('nickname', 'holder_name'),
    'get_cards': ('merchant',), 'get_savings': ('label',),
    'get_bills': ('provider',), 'get_spending_summary': ('description', 'label'),
    'get_support_tickets': ('subject', 'description'), 'list_tickets': ('subject', 'description'),
    'read_ticket': ('subject', 'description', 'body'),
    'search_knowledge': ('content', 'text', 'title'), 'list_audit_events': ('detail', 'details'),
}
SENSITIVE = frozenset(('to_account', 'amount_vnd', 'limit_vnd', 'account_id', 'from_account', 'card_id', 'bill_id', 'ticket_id', 'user_id',
                       'target_account', 'email', 'phone', 'new_email', 'new_phone'))


class ParameterSourceDenied(HTTPException):
    def __init__(self, field, sources):
        super().__init__(403, 'PARAM_NOT_FROM_USER')
        self.source_ids = sources
        self.audit = {'field': field, 'untrusted_hash_match': bool(sources),
                      'secondary_reason': 'PARAM_FROM_UNTRUSTED' if sources else None}


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=13').fetchone():
        return
    conn.execute("ALTER TABLE agent_runs ADD COLUMN context_label TEXT NOT NULL DEFAULT 'TRUSTED'")
    conn.execute("ALTER TABLE agent_runs ADD COLUMN source_ids_json TEXT NOT NULL DEFAULT '[]'")
    conn.execute('INSERT INTO schema_migrations VALUES (13,?)', (stamp,))


def inherited_label(conn, conversation_id):
    return 'UNTRUSTED' if conn.execute("SELECT 1 FROM agent_runs WHERE conversation_id=? AND context_label='UNTRUSTED' LIMIT 1", (conversation_id,)).fetchone() else 'TRUSTED'


def observe(conn, run, tool, result):
    from .quarantine import source_id
    fields = FIELD_TRUST.get(tool, ())
    sources = set()
    fingerprints = {}
    def walk(value, record='result'):
        if isinstance(value, list):
            for item in value:
                walk(item, record)
        elif isinstance(value, dict):
            record = str(value.get('id') or value.get('transaction_id') or value.get('document_id') or record)
            if any(isinstance(value.get(key), str) and value[key].strip() for key in fields):
                sources.add(source_id(tool, record))
                for key in fields:
                    text = value.get(key)
                    if isinstance(text, str):
                        tokens = re.findall(r'[\w-]+', text.lower())
                        tokens += [re.sub(r'[,._]', '', token) for token in re.findall(r'\d[\d,._]*', text)]
                        for token in tokens:
                            fingerprints.setdefault(hashlib.sha256(token.encode()).hexdigest(), set()).add(source_id(tool, record))
            for item in value.values():
                if isinstance(item, (dict, list)):
                    walk(item, record)
    walk(result)
    if sources:
        old = conn.execute('SELECT source_ids_json,untrusted_values_json FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
        merged = sorted(set(json.loads(old[0])) | sources)
        conn.execute("UPDATE agent_runs SET context_label='UNTRUSTED',source_ids_json=? WHERE id=?", (json.dumps(merged), run['id']))
        previous = json.loads(old[1])
        merged_hashes = {key: set(values) for key, values in previous.items()}
        for key, values in fingerprints.items():
            merged_hashes.setdefault(key, set()).update(values)
        conn.execute('UPDATE agent_runs SET untrusted_values_json=? WHERE id=?', (json.dumps({key: sorted(merged_hashes[key]) for key in sorted(merged_hashes)[:8192]}), run['id']))
    return sorted(sources)


def user_value(text, key, value):
    """Compare normalized complete values, never a prefix of a different ID/amount."""
    normalized = re.sub(r'[\s-]+', '', str(value)).casefold()
    if not normalized:
        return False
    boundary = r'[\w@.+-]' if 'email' in key else r'[\w-]'
    pattern = r'(?<!' + boundary + ')' + r'[\s-]*'.join(re.escape(char) for char in normalized) + r'(?!' + boundary + ')'
    if re.search(pattern, text.casefold()):
        return True
    if key in ('amount_vnd', 'limit_vnd') and type(value) is int:
        # The bank's existing numeric parser normalizes explicit monetary
        # spelling such as 10.000 VND / 10k. Do not trust a supplied canonical
        # argument alone, and never parse memo text as an authorized amount.
        from ..banking_workflow import CONTENT, amount_in
        from ..faq import fold
        head = CONTENT.split(fold(text))[0]
        head = re.sub(r'\b(?:acc|card|bill|tkt)-[\w-]+', ' ', head)
        return amount_in(head) == value
    return False


def validate(conn, run, tool, args, intent):
    row = conn.execute('SELECT context_label,source_ids_json,untrusted_values_json FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
    origins = {}
    for key, value in args.items():
        if key not in SENSITIVE or value is None:
            continue
        if user_value(intent['text'], key, value):
            origins[key] = 'user'
            continue
        # Existing payment flow has a server-selected primary funding account.
        # The model cannot choose another account through this exception.
        if (tool, key) in (('prepare_bill_payment', 'account_id'), ('prepare_transfer', 'from_account')):
            primary = conn.execute('SELECT id FROM accounts WHERE owner_id=? ORDER BY id LIMIT 1', (run['owner_id'],)).fetchone()
            if primary and primary[0] == value:
                origins[key] = 'bank_default'
                continue
        hashes = json.loads(row[2]) if row and row[0] == 'UNTRUSTED' else {}
        sources = hashes.get(hashlib.sha256(str(value).lower().encode()).hexdigest(), [])
        denied = ParameterSourceDenied(key, sources)
        emit(conn, 'policy_decision', run_id=run['id'], tool=tool, decision='DENY',
             reason='PARAM_NOT_FROM_USER', rule_id='T4-bind', source_ids=sources,
             detail=denied.audit)
        raise denied
    return origins


def parameter_sources(conn, run, args):
    row = conn.execute('SELECT untrusted_values_json FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
    values = json.loads(row[0]) if row else {}
    sources = set()
    for key, value in args.items():
        if key in SENSITIVE:
            sources.update(values.get(hashlib.sha256(str(value).lower().encode()).hexdigest(), ()))
    return sorted(sources)


def inherit(conn, conversation_id, run_id):
    sources, hashes = set(), {}
    for row in conn.execute("SELECT source_ids_json,untrusted_values_json FROM agent_runs WHERE conversation_id=? AND id!=? AND context_label='UNTRUSTED'", (conversation_id, run_id)):
        sources.update(json.loads(row[0]))
        for key, values in json.loads(row[1]).items():
            hashes.setdefault(key, set()).update(values)
    if sources:
        conn.execute("UPDATE agent_runs SET context_label='UNTRUSTED',source_ids_json=?,untrusted_values_json=? WHERE id=?", (json.dumps(sorted(sources)), json.dumps({key: sorted(hashes[key]) for key in sorted(hashes)[:8192]}), run_id))
