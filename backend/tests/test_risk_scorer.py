import json
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_risk_is_monotone_with_tier_floors_and_five_nearest_cases(client):
    from app.risk.scorer import score
    from app.risk.cases import nearest, record
    base = {'tool': 'prepare_transfer', 'tier': 'financial', 'context_label': 'TRUSTED', 'recipient_new': False, 'amount_bucket': 'small', 'config': 'D'}
    valid = score(base)
    assert valid['band'] == 'medium'
    new = score({**base, 'recipient_new': True})
    tainted = score({**base, 'recipient_new': True, 'context_label': 'UNTRUSTED'})
    assert valid['score'] <= new['score'] <= tainted['score']
    assert tainted['band'] == 'very_high'
    with get_db().connect() as conn:
        for i in range(8):
            record(conn, 'risk-fixture-' + str(i), {**base, 'amount_bucket': 'small' if i < 5 else 'large'}, 'deny_and_flag' if i == 0 else 'allow', 20)
        neighbors = nearest(conn, base)
        assert len(neighbors) == 5
        assert neighbors[0]['distance'] == 0
        assert score(base, neighbors)['score'] > valid['score']
        assert all('text' not in json.loads(r[0]) for r in conn.execute('SELECT features_json FROM risk_cases'))


def test_tainted_new_recipient_cannot_request_otp_until_cooling_off(client):
    who = login(client)
    with get_db().connect() as conn:
        conn.execute("DELETE FROM verified_payees WHERE owner_id='alice' AND to_account='ACC-BOB-001'")
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001 content lunch')
    assert client.post('/api/agent/tools', headers=token, json={'name': 'get_recent_transactions', 'arguments': {}}).json()['decision'] == 'ALLOW'
    proposal = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert proposal['decision'] == 'ALLOW', proposal
    approved = client.post('/api/agent/approvals/' + proposal['result']['approval_id'], headers=who, json={'approve': True})
    assert approved.status_code == 200
    transfer_id = approved.json()['draft_id']
    denied = client.post('/api/transfers/' + transfer_id + '/otp', headers=who)
    assert denied.status_code == 400 and denied.json()['detail'] == 'RECIPIENT_COOLING_OFF'
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM dev_outbox WHERE challenge_id=?', ('transfer:' + transfer_id,)).fetchone()[0] == 0
        assert conn.execute('SELECT balance_vnd FROM accounts WHERE id=?', ('ACC-ALICE-001',)).fetchone()[0] == 12500000
        conn.execute('UPDATE approval_risk SET not_before=0 WHERE run_id=?', (grant['run_id'],))
    from tests.stepup_helpers import verify_new_payee
    verify_new_payee(client, who, transfer_id)
    assert client.post('/api/transfers/' + transfer_id + '/otp', headers=who).status_code == 200


def test_denied_action_records_flagged_features_with_legitimate_control(client):
    who = login(client)
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001')
    denied = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert denied['decision'] == 'DENY'
    with get_db().connect() as conn:
        case = conn.execute('SELECT * FROM risk_cases WHERE run_id=?', (grant['run_id'],)).fetchone()
        assert case['decision'] == 'deny_and_flag'
        assert json.loads(case['features_json'])['tool'] == 'prepare_transfer'
        assert case['score'] >= 20
    _, _, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001')
    valid = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert valid['decision'] == 'ALLOW'
