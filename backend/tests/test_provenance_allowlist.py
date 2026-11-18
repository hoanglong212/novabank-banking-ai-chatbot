"""A model value needs positive user/bank provenance even when hashes miss it."""
import json

from fastapi import HTTPException
import pytest

from tests.acceptance_helpers import client, get_db, login
from tests.test_AI_12 import run_for


@pytest.mark.parametrize('key,value,memo', [
    ('to_account', 'ACC-BOB-001', 'acc bob 001'),
    ('amount_vnd', 20000, 'updated amount 20000'),
    ('account_id', 'ACC-BOB-001', 'acc bob 001'),
    ('new_email', 'changed@example.invalid', 'new contact'),
    ('new_phone', '+84912345678', 'new contact'),
])
def test_sensitive_value_missing_from_user_is_denied_even_if_source_hash_misses(client, key, value, memo):
    from app.agent.provenance import observe, validate
    who = login(client)
    _, grant, _ = run_for(client, who, 'Transfer 10000 VND to ACC-CHARLIE-001')
    with get_db().connect() as conn:
        run = dict(conn.execute('SELECT * FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone())
        observe(conn, run, 'get_transaction_status', {'id': 'TX-R2', 'description': memo})
        with pytest.raises(HTTPException) as denied:
            validate(conn, run, 'prepare_transfer', {key: value}, {'text': 'Transfer 10000 VND to ACC-CHARLIE-001', 'arguments': {}})
        assert denied.value.detail == 'PARAM_NOT_FROM_USER'
        event = conn.execute("SELECT reason,rule_id,detail_json FROM security_events WHERE run_id=? AND rule_id='T4-bind' ORDER BY rowid DESC LIMIT 1",
                             (run['id'],)).fetchone()
        assert tuple(event[:2]) == ('PARAM_NOT_FROM_USER', 'T4-bind')
        assert json.loads(event[2])['field'] == key
        if key == 'amount_vnd':
            assert json.loads(event[2])['secondary_reason'] == 'PARAM_FROM_UNTRUSTED'


def test_user_normalization_and_bank_primary_default_are_positive_sources(client):
    from app.agent.provenance import validate
    who = login(client)
    _, grant, _ = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001')
    with get_db().connect() as conn:
        run = dict(conn.execute('SELECT * FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone())
        args = {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}
        for text in ('Transfer 10000 VND to ACC-BOB-001', 'Transfer 10000 VND to acc bob 001'):
            assert validate(conn, run, 'prepare_transfer', args, {'text': text, 'arguments': {}}) == {
                'to_account': 'user', 'amount_vnd': 'user'}
        for text in ('Transfer 10.000 VND to ACC-BOB-001', 'Transfer 10k to ACC-BOB-001'):
            assert validate(conn, run, 'prepare_transfer', args, {'text': text, 'arguments': {}})['amount_vnd'] == 'user'
        assert validate(conn, run, 'prepare_bill_payment', {'account_id': 'ACC-ALICE-001'},
                        {'text': 'Pay my bill', 'arguments': {}})['account_id'] == 'bank_default'
    good = client.post('/api/agent/tools', headers={'Authorization': 'Bearer ' + grant['delegated_token']},
        json={'name': 'prepare_transfer', 'arguments': args}).json()
    assert good['decision'] == 'ALLOW'
    assert good['result']['status'] == 'PENDING'


def test_model_argument_cannot_borrow_a_substring_or_unverified_canonical_value(client):
    from app.agent.provenance import validate
    who = login(client)
    _, grant, _ = run_for(client, who, 'Transfer 100000 VND to ACC-BOB-0019')
    with get_db().connect() as conn:
        run = dict(conn.execute('SELECT * FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone())
        for args in ({'to_account': 'ACC-BOB-001'}, {'amount_vnd': 10000}):
            with pytest.raises(HTTPException, match='PARAM_NOT_FROM_USER'):
                validate(conn, run, 'prepare_transfer', args,
                         {'text': 'Transfer 100000 VND to ACC-BOB-0019', 'arguments': args})


def test_gateway_retains_allowlist_rule_and_secondary_hash_reason_after_rollback(client):
    from app.agent.provenance import observe
    who = login(client)
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-CHARLIE-001')
    with get_db().connect() as conn:
        run = dict(conn.execute('SELECT * FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone())
        observe(conn, run, 'get_transaction_status', {'id': 'TX-R2', 'description': 'proposed amount 20000'})
    response = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer',
        'arguments': {'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 20000}}).json()
    assert response['reason'] == 'PARAM_NOT_FROM_USER' and response['halt'] is True
    with get_db().connect() as conn:
        rows = list(conn.execute("SELECT rule_id,detail_json FROM security_events WHERE event='policy_decision' AND run_id=? AND reason='PARAM_NOT_FROM_USER'", (run['id'],)))
        assert any(row[0] == 'T4-bind' and json.loads(row[1]).get('secondary_reason') == 'PARAM_FROM_UNTRUSTED' for row in rows)
        assert conn.execute('SELECT COUNT(*) FROM tool_approvals WHERE run_id=?', (run['id'],)).fetchone()[0] == 0
