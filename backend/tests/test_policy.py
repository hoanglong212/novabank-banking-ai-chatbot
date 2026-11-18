import json
import time
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_policy_rules_and_unreadable_files_fail_closed_with_positive_control(client, tmp_path, monkeypatch):
    from app.agent import policy
    facts = {'tool': 'prepare_transfer', 'role': 'customer', 'context': 'UNTRUSTED', 'arg_not_from_user': True, 'recipient_new': True, 'args': {'amount_vnd': 10000}}
    assert policy.evaluate('C', facts) == {'action': 'deny_and_flag', 'rule_id': 'T4-bind'}
    assert policy.evaluate('C', {**facts, 'context': 'TRUSTED', 'arg_not_from_user': False})['action'] in ('approve_with_otp', 'band_high')
    for config in 'ABCD':
        assert policy.load(config)['layers']['approval_otp'] is True
    monkeypatch.setattr(policy, 'POLICY_DIR', tmp_path)
    (tmp_path / 'D.json').write_text('{broken', encoding='utf-8')
    assert policy.evaluate('D', facts)['action'] == 'deny'
    assert policy.evaluate('D', facts)['rule_id'] == 'POLICY_UNAVAILABLE'


def test_invalid_risk_configuration_fails_closed_and_default_d_cannot_request_baseline(client, tmp_path, monkeypatch):
    from app.agent import policy
    original = policy.load('D')
    _, _, token = run_for(client, login(client, 'admin'))
    assert client.get('/api/agent/context', headers=token).json()['profile'] == 'defended'
    monkeypatch.setattr(policy, 'POLICY_DIR', tmp_path)
    for bad in (float('nan'), -1, True, 90000):
        original['risk']['new_recipient_wait_seconds'] = bad
        (tmp_path / 'D.json').write_text(json.dumps(original), encoding='utf-8')
        assert policy.evaluate('D', {}) == {'action': 'deny', 'rule_id': 'POLICY_UNAVAILABLE'}
    original['risk']['new_recipient_wait_seconds'] = 60
    (tmp_path / 'D.json').write_text(json.dumps(original), encoding='utf-8')
    assert policy.evaluate('D', {})['action'] == 'approve_with_otp'


def test_policy_conditions_are_typed_and_unknown_operators_are_rejected(client, tmp_path, monkeypatch):
    from app.agent import policy
    original = policy.load('D')
    original['rules'] = [{'id': 'amount-limit', 'priority': 1, 'when': {'tool': 'prepare_transfer', 'role': 'customer', 'args': {'amount_vnd': {'gte': 1000000}}}, 'then': 'deny'}, {'id': 'valid', 'priority': 2, 'when': {}, 'then': 'allow'}]
    monkeypatch.setattr(policy, 'POLICY_DIR', tmp_path)
    target = tmp_path / 'D.json'
    target.write_text(json.dumps(original), encoding='utf-8')
    assert policy.evaluate('D', {'tool': 'prepare_transfer', 'role': 'customer', 'args': {'amount_vnd': 1000000}})['rule_id'] == 'amount-limit'
    assert policy.evaluate('D', {'tool': 'prepare_transfer', 'role': 'customer', 'args': {'amount_vnd': 1000}})['rule_id'] == 'valid'
    original['rules'][0]['when']['unknown_condition'] = True
    target.write_text(json.dumps(original), encoding='utf-8')
    assert policy.evaluate('D', {})['rule_id'] == 'POLICY_UNAVAILABLE'


def test_lab_configs_are_named_scoped_expiring_and_default_to_d(client, monkeypatch):
    monkeypatch.setenv('ENV', 'production')
    admin, alice, bob = login(client, 'admin'), login(client), login(client, 'bob')
    payload = {'config': 'C', 'users': ['alice'], 'minutes': 2}
    assert client.put('/api/admin/agent-gateway', headers=admin, json=payload).status_code == 403
    monkeypatch.setenv('ENV', 'lab')
    changed = client.put('/api/admin/agent-gateway', headers=admin, json=payload)
    assert changed.status_code == 200, changed.text
    _, _, alice_token = run_for(client, alice)
    assert client.get('/api/agent/context', headers=alice_token).json()['config'] == 'C'
    _, _, bob_token = run_for(client, bob)
    assert client.get('/api/agent/context', headers=bob_token).json()['config'] == 'D'
    with get_db().connect() as conn:
        value = json.loads(conn.execute("SELECT value_json FROM bank_settings WHERE key='agent_gateway'").fetchone()[0])
        value['expires_at'] = int(time.time()) - 1
        conn.execute("UPDATE bank_settings SET value_json=? WHERE key='agent_gateway'", (json.dumps(value),))
    assert client.get('/api/agent/context', headers=alice_token).status_code == 401
    _, _, fresh = run_for(client, alice)
    assert client.get('/api/agent/context', headers=fresh).json()['config'] == 'D'
