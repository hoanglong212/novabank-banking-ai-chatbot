"""S5 (Tier 5): no status claims on a non-action turn. S6 (Tier 1c): an anomalous stop cancels the run's proposals."""
import json

import pytest

from app.agent.quarantine import HALTED
from app.agent_output import NOT_DONE
from app.dependencies import get_db
from tests.conftest import sign_in
from tests.test_week7 import grant_for

PIN = 'How do I change my card PIN?'


def preview(client, token, answer):
    response = client.post('/api/agent/preview', headers=token, json={'answer': answer})
    assert response.status_code == 200, response.text
    return response.json()['text']


@pytest.mark.parametrize('claim', ['Tôi đã chuyển 5.000.000 VND thành công cho bạn.',
                                   'Your transfer of 100,000 VND has been confirmed and is now being processed.'])
def test_S5_status_claim_on_a_non_action_turn_is_replaced(client, alice, claim):
    _, _, token = grant_for(client, alice, PIN)
    assert preview(client, token, 'You can change it in Cards. ' + claim) == NOT_DONE


@pytest.mark.parametrize('answer', ['You can change your card PIN in the Cards screen under Security.',
                                    'Transfers to other banks usually arrive within one business day.'])
def test_S5_answer_without_a_status_claim_passes_unchanged(client, alice, answer):
    _, _, token = grant_for(client, alice, PIN)
    assert preview(client, token, answer) == answer


def test_S6_anomalous_stop_cancels_every_pending_proposal_of_the_run(client, alice, monkeypatch):
    monkeypatch.setenv('ENV', 'lab')
    admin = sign_in(client, 'admin', 'Admin@2026')
    assert client.put('/api/admin/agent-gateway', headers=admin, json={'config': 'B', 'users': ['alice'], 'minutes': 60}).status_code == 200
    _, grant, token = grant_for(client, alice, 'Số dư tài khoản của tôi là bao nhiêu?')
    results = [client.post('/api/agent/tools', headers=token, json={'name': name, 'arguments': args}).json() for name, args in (
        ('prepare_transfer', {'to_account': 'ACC-BOB-001', 'amount_vnd': 5000000}), ('list_customers', {'limit': 50}),
        ('prepare_transfer', {'to_account': 'ACC-BOB-001', 'amount_vnd': 4000000}), ('list_accounts', {'limit': 50}))]
    assert [r['decision'] for r in results] == ['ALLOW', 'DENY', 'ALLOW', 'DENY'] and results[-1]['halt'] is True
    finished = client.post('/api/agent/finish', headers=token, json={
        'answer': 'I prepared it.', 'latency_ms': 1, 'status': 'FAILED', 'termination_reason': 'ANOMALOUS_SEQUENCE'})
    assert finished.status_code == 200, finished.text
    assert finished.json()['message']['content'] == HALTED
    with get_db().connect() as conn:
        rows = conn.execute('SELECT status,response_json FROM tool_approvals WHERE run_id=?', (grant['run_id'],)).fetchall()
        halted = conn.execute("SELECT reason FROM security_events WHERE run_id=? AND event='run_halted'", (grant['run_id'],)).fetchall()
    assert len(rows) == 2
    assert all(r[0] == 'REJECTED' and json.loads(r[1]) == {'reason': 'ANOMALOUS_SEQUENCE'} for r in rows)
    assert [r[0] for r in halted] == ['ANOMALOUS_SEQUENCE']
