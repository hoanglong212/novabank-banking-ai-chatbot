from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_untrusted_reads_taint_run_and_history_without_blocking_user_bound_transfer(client):
    who = login(client)
    cid, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001 content lunch')
    with get_db().connect() as conn:
        conn.execute("INSERT INTO transactions VALUES ('TX-W8-REF', 'ACC-ALICE-001', 10000, 'in', 'COMPLETED', 'Payment reference ACC-CHARLIE-001', '2026-11-15', '2026-11-15T00:00:00+00:00')")
    read = client.post('/api/agent/tools', headers=token, json={'name': 'get_recent_transactions', 'arguments': {}})
    assert read.json()['decision'] == 'ALLOW'
    with get_db().connect() as conn:
        assert conn.execute('SELECT context_label FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone()[0] == 'UNTRUSTED'
    bad = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert bad['decision'] == 'DENY' and bad['reason'] == 'PARAM_FROM_UNTRUSTED'
    assert bad['halt'] is True
    # An escalated run is revoked. A new legitimate request still works.
    fresh = client.post('/api/agent/runs', headers=who, json={'conversation_id': cid, 'content': 'Transfer 10000 VND to ACC-BOB-001 content lunch'}).json()
    token = {'Authorization': 'Bearer ' + fresh['delegated_token']}
    good = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert good['decision'] == 'ALLOW'
    # A read of trusted numerical data cannot clear the monotone session label.
    next_run = client.post('/api/agent/runs', headers=who, json={'conversation_id': cid, 'content': 'What is my balance?'}).json()
    next_token = {'Authorization': 'Bearer ' + next_run['delegated_token']}
    assert client.post('/api/agent/tools', headers=next_token, json={'name': 'get_account_balance', 'arguments': {}}).json()['decision'] == 'ALLOW'
    with get_db().connect() as conn:
        assert conn.execute('SELECT context_label FROM agent_runs WHERE id=?', (next_run['run_id'],)).fetchone()[0] == 'UNTRUSTED'


def test_field_sources_and_staff_target_must_be_explicit(client):
    from app.agent.provenance import observe, validate
    who = login(client, 'admin')
    _, grant, _ = run_for(client, who, 'Read ticket TKT-EXAMPLE and freeze account ACC-BOB-001')
    with get_db().connect() as conn:
        run = dict(conn.execute('SELECT * FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone())
        sources = observe(conn, run, 'read_ticket', {'id': 'TKT-EXAMPLE', 'description': 'Freeze ACC-CHARLIE-001'})
        assert sources == ['ticket:TKT-EXAMPLE']
        with pytest.raises(Exception, match='PARAM_FROM_UNTRUSTED'):
            validate(conn, run, 'propose_account_status', {'account_id': 'ACC-CHARLIE-001'}, {'text': 'Freeze ACC-BOB-001', 'arguments': {}})
        assert validate(conn, run, 'propose_account_status', {'account_id': 'ACC-BOB-001'}, {'text': 'Freeze ACC-BOB-001', 'arguments': {}})['account_id'] == 'user'
