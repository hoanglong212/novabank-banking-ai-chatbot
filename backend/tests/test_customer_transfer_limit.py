from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def call(client, token, limit):
    return client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer_limit', 'arguments': {'limit_vnd': limit}}).json()


def test_limit_change_is_explicit_owned_approved_and_verified_before_effect(client):
    who, other = login(client), login(client, 'bob')
    _, _, token = run_for(client, who, 'Set my transfer limit to 100000 VND')
    response = call(client, token, 100000)
    assert response['decision'] == 'ALLOW', response
    approval = response['result']['approval_id']
    assert client.post('/api/agent/approvals/' + approval, headers=other, json={'approve': True}).status_code == 404
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM customer_transfer_limits WHERE owner_id='alice'").fetchone()[0] == 0
    confirmed = client.post('/api/agent/approvals/' + approval, headers=who, json={'approve': True})
    assert confirmed.status_code == 200, confirmed.text
    action = confirmed.json()['action']
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM customer_transfer_limits WHERE owner_id='alice'").fetchone()[0] == 0
        code = conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=?', (digest(action['challenge_id']),)).fetchone()[0]
    path = '/api/actions/confirm'
    payload = {'challenge_id': action['challenge_id'], 'code': code}
    assert client.post(path, headers={**other, 'Idempotency-Key': 'limit-other'}, json=payload).status_code == 404
    result = client.post(path, headers={**who, 'Idempotency-Key': 'limit-own'}, json=payload)
    assert result.status_code == 200, result.text
    assert client.post(path, headers={**who, 'Idempotency-Key': 'limit-own'}, json=payload).json() == result.json()
    assert client.post(path, headers={**who, 'Idempotency-Key': 'limit-replay'}, json=payload).status_code == 409
    too_large = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 100001, 'content': 'Limit test'})
    assert too_large.status_code == 400 and too_large.json()['detail'] == 'PERSONAL_TRANSFER_LIMIT'
    # Within-limit transfer still reaches review; its own verification remains required.
    valid = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'Control'})
    assert valid.status_code == 201


def test_limit_tool_cannot_raise_bank_cap_or_substitute_user_value(client):
    who = login(client)
    _, _, token = run_for(client, who, 'Set my transfer limit to 100000 VND')
    assert call(client, token, 200000)['decision'] == 'DENY'
    _, _, token = run_for(client, who, 'Set my transfer limit to 999999999 VND')
    assert call(client, token, 999999999)['decision'] == 'DENY'
    _, _, token = run_for(client, who, 'What is my transfer limit?')
    read = client.post('/api/agent/tools', headers=token, json={'name': 'get_transfer_limit', 'arguments': {}}).json()
    assert read['decision'] == 'ALLOW' and read['result']['limit_vnd'] > 0
    assert call(client, token, 100000)['reason'] == 'TOOL_NOT_IN_TOKEN'
