import json
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_review_is_bank_generated_and_otp_names_exact_payment(client):
    who = login(client)
    with get_db().connect() as conn:
        conn.execute("DELETE FROM verified_payees WHERE owner_id='alice' AND to_account='ACC-BOB-001'")
    _, grant, token = run_for(client, who, 'Transfer 10000 VND to ACC-BOB-001 content lunch')
    proposal = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert proposal['decision'] == 'ALLOW'
    key = proposal['result']['approval_id']
    assert client.post('/api/agent/finish', headers=token, json={'answer': 'MODEL_SAYS_APPROVED_AND_SAFE', 'latency_ms': 1}).status_code == 200
    detail = client.get('/api/agent/approvals/' + key, headers=who).json()
    review = detail['review']
    assert review['new_recipient'] is True
    assert review['risk_band'] == 'medium'
    assert review['parameter_sources']['to_account'] == 'user'
    assert review['parameter_sources']['amount_vnd'] == 'user'
    assert review['rule_ids'] == ['bank-approval']
    assert 'MODEL_SAYS_APPROVED' not in json.dumps(detail)
    assert review['title'] == 'Review your transfer'
    approved = client.post('/api/agent/approvals/' + key, headers=who, json={'approve': True}).json()
    transfer_id = approved['draft_id']
    from tests.stepup_helpers import verify_new_payee
    verify_new_payee(client, who, transfer_id)
    assert client.post('/api/transfers/' + transfer_id + '/otp', headers=who).status_code == 200
    with get_db().connect() as conn:
        body = conn.execute('SELECT body FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1', ('transfer:' + transfer_id,)).fetchone()[0]
    assert '10,000 VND' in body and 'BOB TRAN' in body and 'NovaBank' in body and '-001' in body
    assert 'ACC-BOB-001' not in body
    # Positive ownership control: an unrelated user cannot see this review.
    assert client.get('/api/agent/approvals/' + key, headers=login(client, 'bob')).status_code == 404
