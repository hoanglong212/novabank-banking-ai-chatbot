"""Lab switch for the agent gateway, and the per-call ALLOW/DENY log used to compare gateway off with on.

Gateway ON (default) is every bank-side AI guard: the prompt tripwire on the user's message, the tool boundary (role
allowlist, binding to the latest request, proposal checks, staff read checks), source screening, the two-denial stop
and the output filter on the answer. Gateway OFF is a measurement mode for ENV=demo/lab only: messages reach the model
unfiltered, the bank runs whatever tool the model asks for with the model's own arguments, and the answer is stored as
written. Kept in both modes: sign-in and session checks, secret redaction, schema validation, the 8-call budget,
owner-scoped data queries, and the human approval plus OTP/PIN verification before anything changes.
"""
import csv
import io
import json
from pathlib import Path
from fastapi import HTTPException
from .config import setting
from .database import now
from .posting import audit

LAB_ENVIRONMENTS = ('demo', 'lab')
COLUMNS = ('created_at', 'gateway', 'profile', 'owner_id', 'role', 'run_id', 'chat_request_id', 'tool_request_id',
           'ordinal', 'tool', 'decision', 'reason', 'latency_ms')


def lab():
    return setting('ENV') in LAB_ENVIRONMENTS


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=10').fetchone():
        return
    conn.execute("ALTER TABLE agent_runs ADD COLUMN gateway TEXT NOT NULL DEFAULT 'on'")
    conn.execute('ALTER TABLE agent_calls ADD COLUMN tool_request_id TEXT')
    conn.execute('INSERT INTO schema_migrations VALUES (10,?)', (stamp,))


def state(conn):
    # Outside a lab environment the gateway is always on, whatever the database or environment says.
    if not lab():
        return 'on'
    row = conn.execute("SELECT value_json FROM bank_settings WHERE key='agent_gateway'").fetchone()
    value = json.loads(row[0]) if row else setting('AGENT_GATEWAY', 'on')
    return 'off' if value == 'off' else 'on'


def set_state(conn, user, enabled):
    target = 'on' if enabled else 'off'
    if target == 'off' and not lab():
        raise HTTPException(403, 'The gateway can be switched off only when ENV is demo or lab.')
    before = state(conn)
    conn.execute('''INSERT INTO bank_settings VALUES ('agent_gateway',?,?)
                    ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at''', (json.dumps(target), now()))
    audit(conn, user.id, 'SETTING_UPDATED', 'agent_gateway', json.dumps({'before': before, 'after': target}), now())
    return target


def log_path():
    explicit = setting('GATEWAY_LOG_PATH')
    if explicit:
        return Path(explicit)
    database = setting('DB_PATH')
    return Path(database + '.gateway.jsonl') if database else None


def record(entry):
    """Append one decision as a JSON line (tail it during a Burp/Caido session). The database row stays the record."""
    path = log_path()
    if not path:
        return
    try:
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({k: entry.get(k) for k in COLUMNS}, ensure_ascii=False) + '\n')
    except OSError:
        pass


SELECT = '''SELECT c.created_at, r.gateway, r.profile, r.owner_id, u.role, c.run_id, r.request_id AS chat_request_id,
    c.tool_request_id, c.ordinal, c.name AS tool, c.decision, c.reason, c.latency_ms
    FROM agent_calls c JOIN agent_runs r ON r.id=c.run_id LEFT JOIN users u ON u.id=r.owner_id'''


def entries(conn, gateway=None, decision=None, limit=100, offset=0):
    clauses, params = ["c.decision IN ('ALLOW','DENY','ERROR')"], []
    if gateway:
        clauses.append('r.gateway=?'); params.append(gateway)
    if decision:
        clauses.append('c.decision=?'); params.append(decision)
    where = ' WHERE ' + ' AND '.join(clauses)
    total = conn.execute('SELECT COUNT(*) FROM agent_calls c JOIN agent_runs r ON r.id=c.run_id' + where, params).fetchone()[0]
    rows = conn.execute(SELECT + where + ' ORDER BY c.created_at DESC, c.rowid DESC LIMIT ? OFFSET ?', (*params, limit, offset))
    return {'items': [dict(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}


def metrics(conn):
    result = {g: {'runs': 0, 'calls': 0, 'allow': 0, 'deny': 0, 'error': 0, 'deny_reasons': {}} for g in ('off', 'on')}
    for gateway, runs in conn.execute('SELECT gateway, COUNT(*) FROM agent_runs GROUP BY gateway'):
        result.setdefault(gateway, {'runs': 0, 'calls': 0, 'allow': 0, 'deny': 0, 'error': 0, 'deny_reasons': {}})['runs'] = runs
    for gateway, decision, reason, count in conn.execute('''SELECT r.gateway, c.decision, c.reason, COUNT(*) FROM agent_calls c
            JOIN agent_runs r ON r.id=c.run_id WHERE c.decision IN ('ALLOW','DENY','ERROR') GROUP BY 1,2,3'''):
        bucket = result.setdefault(gateway, {'runs': 0, 'calls': 0, 'allow': 0, 'deny': 0, 'error': 0, 'deny_reasons': {}})
        bucket['calls'] += count
        bucket[decision.lower()] += count
        if decision == 'DENY':
            bucket['deny_reasons'][reason] = count
    return result


def csv_text(conn, gateway=None):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    for row in conn.execute(SELECT + " WHERE c.decision IN ('ALLOW','DENY','ERROR')" + (' AND r.gateway=?' if gateway else '')
                            + ' ORDER BY c.created_at, c.rowid', (gateway,) if gateway else ()):
        writer.writerow(dict(row))
    return out.getvalue()
