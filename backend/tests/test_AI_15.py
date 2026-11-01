from tests.acceptance_helpers import *
from tests.agent_acceptance_helpers import run_for, exercise, calls


def test_AI_15_trace_metadata_and_payloads_do_not_persist_raw_identity_or_secrets(client, monkeypatch):
    who = login(client); _, grant, token = run_for(client, who)
    secret = token['Authorization'][7:]
    responses = [calls(('get_account_balance', {'account_id':'ACC-ALICE-001'})),
        {'content':'ALICE NGUYEN has account ACC-ALICE-001.'}]
    exercise(client, monkeypatch, token, responses)
    detail = client.get('/api/agent/runs/'+grant['run_id'], headers=who).json()
    assert detail['status'] == 'COMPLETED'
    assert detail['model'] and detail['profile'] == 'baseline'
    assert detail['input_tokens'] == 34 and detail['output_tokens'] == 18
    assert detail['latency_ms'] >= 0 and detail['completed_at']
    call = detail['tool_calls'][0]
    assert call['name'] == 'get_account_balance' and call['decision'] == 'ALLOW'
    assert call['latency_ms'] >= 0 and call['reason']
    with get_db().connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM agent_calls WHERE run_id=?',(grant['run_id'],))]
        rows += [dict(conn.execute('SELECT * FROM agent_runs WHERE id=?',(grant['run_id'],)).fetchone())]
    encoded = json.dumps(rows)
    for raw in ('ALICE NGUYEN', 'ACC-ALICE-001', secret):
        assert raw not in encoded, 'Raw value persisted in trace: '+raw[:20]
    assert rows[-1]['vault_json'] == '{}' and rows[-1]['bound_request_json'] == '{}'


def test_AI_15_rejected_arguments_are_redacted_before_trace_storage(client):
    who = login(client); _, grant, token = run_for(client, who)
    secret = token['Authorization'][7:]
    response = client.post('/api/agent/tools', headers=token, json={'name':'get_accounts', 'arguments':{
        'nested': [{'note':'OTP: 739284', 'authorization':secret, 'account':'ACC-ALICE-001', 'name':'ALICE NGUYEN'}]}})
    assert response.json()['decision'] == 'DENY'
    detail = client.get('/api/agent/runs/'+grant['run_id'], headers=who).json()
    wire = json.dumps(detail['tool_calls'])
    for raw in ('739284', secret, 'ACC-ALICE-001', 'ALICE NGUYEN'):
        assert raw not in wire, 'Rejected arguments leaked into trace: '+raw[:20]


def test_AI_15_unfamiliar_structured_identity_is_redacted_even_when_tool_denied(client):
    who=login(client);_,grant,token=run_for(client,who)
    response=client.post('/api/agent/tools',headers=token,json={'name':'prepare_transfer','arguments':{
        'to_name':'UNLISTED RECIPIENT','to_account':'9028341','amount_vnd':1000}})
    assert response.json()['decision']=='DENY'
    wire=json.dumps(client.get('/api/agent/runs/'+grant['run_id'],headers=who).json()['tool_calls'])
    assert 'UNLISTED RECIPIENT' not in wire and '9028341' not in wire
