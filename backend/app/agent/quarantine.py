"""Persistent source isolation and bank-generated terminal responses."""
import json
import time
import uuid
from ..database import now
from ..security_events import emit

PREFIXES = {'get_recent_transactions': 'tx', 'get_transaction_status': 'tx', 'list_transactions': 'tx',
    'read_ticket': 'ticket', 'list_tickets': 'ticket', 'get_support_tickets': 'ticket',
    'get_accounts': 'account', 'list_accounts': 'account', 'get_beneficiaries': 'beneficiary',
    'get_cards': 'card', 'get_savings': 'savings', 'search_knowledge': 'kb', 'get_bills': 'bill'}


def source_id(tool, record):
    return PREFIXES.get(tool, tool) + ':' + str(record)


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=16').fetchone():
        return
    conn.execute('''CREATE TABLE quarantined_sources (source_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,
        reason TEXT NOT NULL,rule_id TEXT NOT NULL,created_at TEXT NOT NULL,released_at TEXT)''')
    conn.execute("ALTER TABLE agent_runs ADD COLUMN untrusted_values_json TEXT NOT NULL DEFAULT '{}'")
    conn.execute('INSERT INTO schema_migrations VALUES (16,?)', (stamp,))


def filtered(conn, tool, value):
    active = {r[0] for r in conn.execute('SELECT source_id FROM quarantined_sources WHERE released_at IS NULL')}
    def walk(item):
        if isinstance(item, list):
            return [walk(child) for child in item]
        if not isinstance(item, dict):
            return item
        record = item.get('id') or item.get('transaction_id') or item.get('document_id')
        if record and source_id(tool, record) in active:
            return {'quarantined': True}
        # read_ticket's thread is a sibling of its ticket record: isolate the whole result.
        if tool == 'read_ticket' and isinstance(item.get('ticket'), dict) and source_id(tool, item['ticket'].get('id')) in active:
            return {'quarantined': True}
        return {key: walk(child) for key, child in item.items()}
    return walk(value)


def _owner(conn, source, fallback):
    prefix, _, record = source.partition(':')
    tables = {'ticket': 'support_tickets', 'account': 'accounts', 'beneficiary': 'beneficiaries', 'card': 'cards', 'savings': 'savings', 'bill': 'bills'}
    if prefix == 'tx':
        row = conn.execute('SELECT a.owner_id FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE t.id=?', (record,)).fetchone()
    elif prefix in tables:
        row = conn.execute('SELECT owner_id FROM ' + tables[prefix] + ' WHERE id=?', (record,)).fetchone()
    else:
        row = None
    return row[0] if row else fallback


def halt(conn, run, sources, reason, rule_id):
    for source in sources:
        conn.execute('''INSERT INTO quarantined_sources VALUES (?,?,?,?,?,NULL)
            ON CONFLICT(source_id) DO UPDATE SET reason=excluded.reason,rule_id=excluded.rule_id,created_at=excluded.created_at,released_at=NULL''',
            (source, _owner(conn, source, run['owner_id']), reason, rule_id, now()))
    existing = conn.execute('SELECT status FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
    if not existing or existing[0] not in ('READY', 'RUNNING'):
        return None
    from ..risk.cases import finish
    finish(conn, run['id'])
    conn.execute("UPDATE tool_approvals SET status='REJECTED',response_json=? WHERE run_id=? AND status='PENDING'", (json.dumps({'reason': reason}), run['id']))
    emit(conn, 'run_halted', run_id=run['id'], event_id='halt:' + run['id'], reason=reason, rule_id=rule_id, source_ids=sources)
    conn.execute("UPDATE agent_runs SET status='CANCELLED',completed_at=?,termination_reason='ANOMALOUS_SEQUENCE',bound_request_json='{}',vault_json='{}' WHERE id=?", (now(), run['id']))
    text = ('I stopped this request because a source or proposed action did not pass the bank checks. '
            'No payment has been made by the assistant. Please review the details in the banking screens or contact support.')
    message = {'id': uuid.uuid4().hex, 'conversation_id': run['conversation_id'], 'role': 'assistant', 'content': text, 'created_at': now()}
    conn.execute('INSERT INTO messages VALUES (:id,:conversation_id,:role,:content,:created_at)', message)
    conn.execute('UPDATE conversations SET updated_at=? WHERE id=?', (message['created_at'], run['conversation_id']))
    email = conn.execute('SELECT email FROM users WHERE id=?', (run['owner_id'],)).fetchone()[0]
    conn.execute('''INSERT INTO dev_outbox (id,user_id,recipient,kind,created_at,challenge_id,body)
        VALUES (?,?,?,'AGENT_HALTED',?,?,?)''', (uuid.uuid4().hex, run['owner_id'], email, int(time.time()), run['id'], text))
    return {'message': message, 'run_id': run['id'], 'response_source': 'gateway', 'tool_events': []}
