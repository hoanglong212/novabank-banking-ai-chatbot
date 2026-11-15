import json
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_security_events_deduplicate_and_redact_without_losing_valid_evidence(client):
    from app.security_events import emit, ladder
    who = login(client)
    _, grant, _ = run_for(client, who)
    with get_db().connect() as conn:
        data = {'run_id': grant['run_id'], 'event_id': 'audit-dedup', 'detail': {'otp': '482916', 'delegated_token': 'secret-jwt', 'text': 'OTP: 123456', 'amount_vnd': 10000}}
        emit(conn, 'policy_decision', **data)
        emit(conn, 'policy_decision', **data)
        rows = conn.execute("SELECT * FROM security_events WHERE id='audit-dedup'").fetchall()
        assert len(rows) == 1
        encoded = rows[0]['detail_json']
        assert '482916' not in encoded and '123456' not in encoded and 'secret-jwt' not in encoded
        assert json.loads(encoded)['amount_vnd'] == 10000
        assert ladder(conn, [grant['run_id']])[grant['run_id']] == {'L1': 0, 'L2': 0, 'L3': 0}


def test_ladder_requires_attack_goal_evidence_not_ordinary_allowed_calls(client):
    from app.security_events import emit, ladder
    who = login(client)
    ids = [run_for(client, who)[1]['run_id'] for _ in range(3)]
    with get_db().connect() as conn:
        for index, run_id in enumerate(ids):
            emit(conn, 'attack_observation', run_id=run_id, detail={'goal_matched': True, 'stage': 'model'})
            if index >= 1:
                emit(conn, 'attack_observation', run_id=run_id, detail={'goal_matched': True, 'stage': 'gateway'})
            if index >= 2:
                emit(conn, 'attack_observation', run_id=run_id, detail={'goal_matched': True, 'stage': 'effect'})
        assert list(ladder(conn, ids).values()) == [
            {'L1': 1, 'L2': 0, 'L3': 0}, {'L1': 1, 'L2': 1, 'L3': 0}, {'L1': 1, 'L2': 1, 'L3': 1}]


def test_run_tool_output_and_cancel_events_are_bank_owned(client):
    who = login(client)
    _, grant, token = run_for(client, who)
    read = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {}})
    assert read.status_code == 200 and read.json()['decision'] == 'ALLOW'
    response = client.post('/api/agent/finish', headers=token, json={'answer': 'Your balance is 123 VND.', 'latency_ms': 1})
    assert response.status_code == 200 and '123 VND' not in response.json()['message']['content']
    with get_db().connect() as conn:
        events = [dict(r) for r in conn.execute('SELECT * FROM security_events WHERE run_id=?', (grant['run_id'],))]
    names = [e['event'] for e in events]
    for name in ('run_started', 'tool_called', 'policy_decision', 'output_filtered'):
        assert names.count(name) == 1
    output = json.loads(next(e['detail_json'] for e in events if e['event'] == 'output_filtered'))
    assert '123 VND' in output['raw'] and '123 VND' not in output['filtered']
    _, cancelled, _ = run_for(client, who)
    url = '/api/agent/runs/' + cancelled['run_id'] + '/cancel'
    assert client.post(url, headers=who).status_code == 200
    assert client.post(url, headers=who).status_code == 200
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM security_events WHERE run_id=? AND event='run_halted'", (cancelled['run_id'],)).fetchone()[0] == 1


def test_approved_transfer_has_once_only_events_and_no_otp_in_evidence(client):
    from tests.conftest import transfer_code
    who = login(client)
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001 content lunch')
    proposal = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert proposal['decision'] == 'ALLOW'
    approval_id = proposal['result']['approval_id']
    for _ in range(2):
        assert client.get('/api/agent/approvals/' + approval_id, headers=who).status_code == 200
    url = '/api/agent/approvals/' + approval_id
    approved = client.post(url, headers=who, json={'approve': True})
    assert approved.status_code == 200
    assert client.post(url, headers=who, json={'approve': True}).json() == approved.json()
    transfer_id = approved.json()['draft_id']
    assert client.post('/api/transfers/' + transfer_id + '/otp', headers=who).status_code == 200
    otp = transfer_code({'id': transfer_id})
    done = client.post('/api/transfers/' + transfer_id + '/confirm', headers={**who, 'Idempotency-Key': 'event-once'}, json={'otp': otp})
    assert done.status_code == 200, done.text
    assert client.post('/api/transfers/' + transfer_id + '/confirm', headers={**who, 'Idempotency-Key': 'event-once'}, json={'otp': otp}).json() == done.json()
    with get_db().connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM security_events WHERE run_id=?', (grant['run_id'],))]
    names = [r['event'] for r in rows]
    for name in ('approval_shown', 'approval_result', 'otp_sent', 'otp_verified', 'transfer_posted'):
        assert names.count(name) == 1, names
    assert otp not in json.dumps(rows)
