import json
from tests.acceptance_helpers import login, get_db
from tests.test_AI_12 import run_for


def install_policy(tmp_path, monkeypatch, rules):
    from app.agent import policy
    document = policy.load('D')
    document['rules'] = rules
    (tmp_path / 'D.json').write_text(json.dumps(document), encoding='utf-8')
    monkeypatch.setattr(policy, 'POLICY_DIR', tmp_path)


def test_new_recipient_condition_reaches_live_policy_evaluation(client, tmp_path, monkeypatch):
    install_policy(tmp_path, monkeypatch, [
        {'id': 'new-recipient-review', 'priority': 1, 'when': {'recipient_new': True}, 'then': 'deny'},
        {'id': 'ordinary', 'priority': 2, 'when': {}, 'then': 'approve_with_otp'},
    ])
    who = login(client)
    with get_db().connect() as conn:
        conn.execute("DELETE FROM verified_payees WHERE owner_id='alice' AND to_account='ACC-CHARLIE-001'")
    _, _, known_token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001')
    known = client.post('/api/agent/tools', headers=known_token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}}).json()
    assert known['decision'] == 'ALLOW'
    _, _, token = run_for(client, who, 'Transfer 10000 VND to ACC-CHARLIE-001')
    result = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 10000}}).json()
    assert result['decision'] == 'DENY' and result['reason'] == 'new-recipient-review', result


def test_custom_deny_and_flag_revokes_run(client, tmp_path, monkeypatch):
    who = login(client)
    _, _, safe_token = run_for(client, who, 'What is my balance?')
    assert client.post('/api/agent/tools', headers=safe_token, json={'name': 'get_account_balance', 'arguments': {}}).json()['decision'] == 'ALLOW'
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001')
    prepared = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}}).json()
    assert prepared['decision'] == 'ALLOW'
    install_policy(tmp_path, monkeypatch, [
        {'id': 'custom-stop', 'priority': 1, 'when': {'tool': 'prepare_transfer'}, 'then': 'deny_and_flag'},
        {'id': 'ordinary', 'priority': 2, 'when': {}, 'then': 'approve_with_otp'},
    ])
    result = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}}).json()
    assert result['decision'] == 'DENY' and result['reason'] == 'custom-stop'
    assert result['halt'] is True, result
    assert client.get('/api/agent/context', headers=token).status_code == 401
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE kind='AGENT_HALTED' AND challenge_id=?", (grant['run_id'],)).fetchone()[0] == 1
        assert conn.execute('SELECT status FROM tool_approvals WHERE id=?', (prepared['result']['approval_id'],)).fetchone()[0] == 'REJECTED'
        assert conn.execute('SELECT decision FROM risk_cases WHERE run_id=?', (grant['run_id'],)).fetchone()[0] == 'deny_and_flag'


def test_stream_upstream_failure_records_terminal_risk_case(client, monkeypatch):
    from contextlib import asynccontextmanager
    import httpx
    from app import routes_agent
    who = login(client)
    _, good, token = run_for(client, who)
    assert client.post('/api/agent/finish', headers=token, json={'answer': 'No verified amount.', 'latency_ms': 1}).status_code == 200
    with get_db().connect() as conn:
        assert conn.execute('SELECT 1 FROM risk_cases WHERE run_id=?', (good['run_id'],)).fetchone()
    class UnavailableAgent:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        @asynccontextmanager
        async def stream(self, *args, **kwargs):
            from app.agent import agent_access
            actor, run = agent_access.authenticate(get_db(), kwargs['headers']['Authorization'])
            proposal = await agent_access.execute_tool(get_db(), actor, run, 'prepare_transfer', {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000})
            assert proposal['decision'] == 'ALLOW'
            raise httpx.ConnectError('Controlled unavailable agent service')
            yield
    monkeypatch.setattr(routes_agent.httpx, 'AsyncClient', UnavailableAgent)
    cid = client.post('/api/conversations', headers=who, json={'title': 'Service outage'}).json()['id']
    response = client.post('/api/conversations/' + cid + '/stream', headers=who, json={'content': 'Transfer 10000 VND to ACC-BOB-001'})
    assert response.status_code == 200 and 'event: error' in response.text
    with get_db().connect() as conn:
        failed = conn.execute('SELECT * FROM agent_runs WHERE conversation_id=?', (cid,)).fetchone()
        assert failed['status'] == 'FAILED'
        assert conn.execute('SELECT 1 FROM risk_cases WHERE run_id=?', (failed['id'],)).fetchone(), 'Terminal FAILED run has no risk case'
        assert failed['vault_json'] == failed['bound_request_json'] == '{}'
        assert failed['termination_reason'] == 'UPSTREAM_ERROR'
        proposals = conn.execute('SELECT status FROM tool_approvals WHERE run_id=?', (failed['id'],)).fetchall()
        assert len(proposals) == 1 and proposals[0][0] == 'REJECTED'


def test_plain_denial_is_not_flagged_because_of_its_rule_name(client, tmp_path, monkeypatch):
    install_policy(tmp_path, monkeypatch, [
        {'id': 'T4-bind', 'priority': 1, 'when': {'tool': 'prepare_transfer'}, 'then': 'deny'},
        {'id': 'ordinary', 'priority': 2, 'when': {}, 'then': 'approve_with_otp'},
    ])
    who = login(client)
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001')
    denied = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}}).json()
    assert denied['decision'] == 'DENY' and denied['halt'] is False
    assert client.get('/api/agent/context', headers=token).status_code == 200
    assert client.post('/api/agent/runs/' + grant['run_id'] + '/cancel', headers=who).status_code == 200
    with get_db().connect() as conn:
        assert conn.execute('SELECT decision FROM risk_cases WHERE run_id=?', (grant['run_id'],)).fetchone()[0] == 'deny'
