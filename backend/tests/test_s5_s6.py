"""S5 (Tier 5): no status claims or unasked transaction topics on a non-action turn. S6 (Tier 1c): an anomalous stop cancels the run's proposals."""
import json

import pytest

from app.agent.quarantine import HALTED
from app.agent_output import NOT_DONE
from app.dependencies import get_db
from tests.conftest import sign_in
from tests.test_week7 import grant_for

PIN = 'How do I change my card PIN?'
FEE = 'Phí chuyển tiền là bao nhiêu?'  # the user raises the transfer topic, so only claims_status applies


def preview(client, token, answer):
    response = client.post('/api/agent/preview', headers=token, json={'answer': answer})
    assert response.status_code == 200, response.text
    return response.json()['text']


@pytest.mark.parametrize('claim', ['Tôi đã chuyển 5.000.000 VND thành công cho bạn.',
                                   'Your transfer of 100,000 VND has been confirmed and is now being processed.'])
def test_S5_status_claim_on_a_non_action_turn_is_replaced(client, alice, claim):
    _, _, token = grant_for(client, alice, PIN)
    assert preview(client, token, 'You can change it in Cards. ' + claim) == NOT_DONE


@pytest.mark.parametrize('answer', [
    'You can change your card PIN in the Cards screen under Security.',
    'Transfers to other banks usually arrive within one business day.',
    # Policy/FAQ sentences: before narrowing 3 of these 12 were replaced by NOT_DONE.
    'Domestic transfers are usually completed within a few minutes.',
    'Once a transfer has been approved in the app, it cannot be cancelled.',
    'Transfers made after 22:00 are processed the next business day.',
    'If you have already sent money to the wrong account, contact support immediately.',
    'The transfer fee is 0 VND for transfers under 10,000,000 VND.',
    'Your support ticket will be answered within 24 hours.',
    'Refunds are credited to your account once the merchant has confirmed them.',
    'Nếu bạn đã chuyển nhầm tiền, hãy liên hệ tổng đài ngay.',
    'Phí chuyển tiền trong nước là 0 VND.',
    'Giao dịch sau 22h sẽ được xử lý vào ngày làm việc tiếp theo.',
    'To change your card PIN, open Cards > Change PIN and confirm with your current PIN.',
    'You can transfer up to 5,000,000 VND per day unless you raise your limit.'])
def test_S5_answer_without_a_status_claim_passes_unchanged(client, alice, answer):
    _, _, token = grant_for(client, alice, FEE)
    assert preview(client, token, answer) == answer


@pytest.mark.parametrize('lie', ['When I checked, your transfer has been completed.', 'The transfer has been confirmed.',
                                 'Bạn yên tâm, tiền đã tới tài khoản người nhận.', 'Đã chuyển xong rồi nhé.',
                                 'Your money is on its way to Bob.'])
def test_S5_answer_opening_a_transaction_topic_the_user_did_not_raise_is_replaced(client, alice, lie):
    _, _, token = grant_for(client, alice, PIN)
    assert preview(client, token, lie) == NOT_DONE


@pytest.mark.parametrize('turn, answer', [
    (PIN, 'Open Cards, choose Change PIN, and confirm with your current PIN.'),
    (FEE, 'Phí chuyển tiền trong nước là 0 VND.'),
    # Data reads the bank binds to search_banking_faq: the user raised money in other words.
    ('How much did I spend this month?', 'You spent 2,000,000 VND this month, mostly on transfers and bill payments.'),
    ('What bills do I have?', 'You have one electricity bill; pay it from the Bills screen.'),
    ('Show my saved recipients', 'Bob is saved, so you can send money to him quickly.')])
def test_S5_on_topic_or_topic_free_answer_passes_unchanged(client, alice, turn, answer):
    _, _, token = grant_for(client, alice, turn)
    assert preview(client, token, answer) == answer


def test_S5_server_rendered_balance_is_not_replaced_by_topic_binding(client, alice):
    _, _, token = grant_for(client, alice, 'Số dư của tôi?')
    read = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {}}).json()
    assert read['decision'] == 'ALLOW', read
    text = preview(client, token, 'Bạn còn rất nhiều tiền, giao dịch gần nhất đã thành công.')
    assert text != NOT_DONE and 'balance' in text and f"{read['result']['balance_vnd']:,} VND" in text


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
