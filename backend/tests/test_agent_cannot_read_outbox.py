"""No agent tool (customer MODELS or staff_tools) can read the simulated mailbox.

Every tool is executed for real, with the gateway OFF so that no intent or role check stops it early,
while every SQL statement is traced. dev_outbox holds live sign-in and transfer codes, so a tool that
touched it would hand them to the model.
"""
import json
from pathlib import Path
from app import database
from app.agent import agent_access
from app import staff_tools
from tests.acceptance_helpers import client, login, get_db  # noqa: F401
from tests.test_agent_gateway import call, switch
from tests.test_week7 import grant_for

TICKET = 'TKT-OUTBOXPROBE'
ARGS = {
    'read_ticket': {'ticket_id': TICKET}, 'get_customer_summary': {'user_id': 'bob'},
    'propose_ticket_reply': {'ticket_id': TICKET, 'body': 'Hello, we are looking into it.'},
    'propose_ticket_status': {'ticket_id': TICKET, 'status': 'IN_PROGRESS'},
    'propose_account_status': {'account_id': 'ACC-BOB-001', 'status': 'FROZEN'},
    'propose_customer_update': {'user_id': 'bob', 'kyc_status': 'VERIFIED'},
    'propose_settings_change': {'transfer_fee_vnd': 0},
    'get_transaction_status': {'transaction_id': 'TX-1001'}, 'search_knowledge': {'query': 'transfer fee'},
    'get_spending_summary': {'month': '2026-11'}, 'prepare_transfer': {'to_account': 'ACC-BOB-001', 'amount_vnd': 1000},
    'prepare_bill_payment': {'bill_id': 'BILL-alice-electricity', 'account_id': 'ACC-ALICE-001'},
    'prepare_support_ticket': {'subject': 'Card help', 'description': 'My card was declined today.'},
    'request_card_freeze': {'card_id': 'CARD-alice-DEBIT'},
}


def test_source_of_the_tool_layer_never_names_the_mailbox():
    root = Path(agent_access.__file__).resolve().parents[1]
    # customer_services also holds profile-change mail delivery, which no tool calls; the trace below covers it.
    for module in (root / 'agent' / 'agent_access.py', root / 'staff_tools.py', root / 'banking_queries.py',
                   root / 'insights.py', root / 'knowledge.py'):
        assert 'dev_outbox' not in module.read_text(encoding='utf-8'), module.name
    assert not [name for name in agent_access.MODELS if 'outbox' in name or 'mail' in name]


def test_every_tool_runs_without_touching_dev_outbox(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    alice, admin = login(client), login(client, 'admin')
    with get_db().connect() as conn:
        conn.execute("INSERT INTO support_tickets VALUES (?,?,?,?,'OPEN',?)", (TICKET, 'alice', 'Card help', 'Declined today.', '2026-11-13T00:00:00+00:00'))
    # A live sign-in code for Bob sits in the outbox while the tools run.
    assert client.post('/api/auth/login', json={'username': 'bob', 'password': 'Bob@2026'}).status_code == 202
    with get_db().connect() as conn:
        secrets = [r[0] for r in conn.execute('SELECT secret_text FROM dev_outbox WHERE secret_text IS NOT NULL')]
    assert secrets
    switch(client, admin, False, users=['alice', 'admin'])

    statements, tracing = [], [False]
    original = database.Database.connect

    def traced(self):
        conn = original(self)
        conn.set_trace_callback(lambda sql: tracing[0] and statements.append(sql))
        return conn
    monkeypatch.setattr(database.Database, 'connect', traced)

    results = {}
    for name in agent_access.MODELS:
        # A fresh run per tool: one run allows only eight calls.
        _, _, token = grant_for(client, admin if name in staff_tools.PERMISSIONS else alice, 'What is my balance?')
        tracing[0] = True
        results[name] = call(client, token, name, ARGS.get(name, {}))
        tracing[0] = False
    not_run = {n: (r['decision'], r['reason']) for n, r in results.items() if r['decision'] != 'ALLOW'}
    assert not not_run, f'Every tool must really execute for this check to mean anything: {not_run}'
    assert statements and not [s for s in statements if 'dev_outbox' in s.lower()]
    exposed = json.dumps(results)
    assert not [code for code in secrets if code in exposed]
