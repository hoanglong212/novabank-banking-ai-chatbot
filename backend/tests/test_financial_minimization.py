import json
import pytest
from app import auth
from tests.acceptance_helpers import client, login, get_db
from tests.test_AI_12 import run_for
from tests.test_customer_products import confirm


def tool(client, token, name, arguments=None):
    response = client.post('/api/agent/tools', headers=token, json={'name': name, 'arguments': arguments or {}})
    assert response.status_code == 200, response.text
    return response.json()


def test_card_status_only_omits_unsolicited_debt_but_explicit_own_debt_is_readable(client, monkeypatch):
    monkeypatch.setenv('ENV', 'lab')
    who, admin = login(client), login(client, 'admin')
    cards = client.get('/api/products/cards', headers=who).json()['items']
    credit = next(card for card in cards if card['kind'] == 'CREDIT')
    action = client.post('/api/products/actions', headers=who, json={'kind': 'CARD_PURCHASE', 'resource_id': credit['id'], 'amount_vnd': 50000, 'label': 'Notebook'}).json()
    assert confirm(client, who, action, 'financial-minimization-purchase').status_code == 200
    assert client.put('/api/admin/agent-gateway', headers=admin, json={'config': 'C', 'users': ['alice'], 'minutes': 2}).status_code == 200
    _, _, token = run_for(client, who, 'Show the status of my cards only')
    result = tool(client, token, 'get_cards')
    assert result['decision'] == 'ALLOW'
    encoded = json.dumps(result['result'])
    for field in ('outstanding_vnd', 'credit_limit_vnd', 'available_credit_vnd', 'transactions'):
        assert field not in encoded
    assert 'ACTIVE' in encoded
    answer = 'Your card debt is 50,000 VND.'
    assert client.post('/api/agent/preview', headers=token, json={'answer': answer}).json()['text'] != answer
    finished = client.post('/api/agent/finish', headers=token, json={'answer': answer, 'latency_ms': 1}).json()
    assert finished['message']['content'] != answer
    _, _, requested = run_for(client, who, 'How much do I owe on my credit card?')
    allowed = tool(client, requested, 'get_cards')
    assert allowed['decision'] == 'ALLOW'
    assert any(card.get('outstanding_vnd') == 50000 for card in allowed['result']['items'])
    shown = client.post('/api/agent/finish', headers=requested, json={'answer': answer, 'latency_ms': 1}).json()['message']['content']
    assert '50,000' in shown and '12,500,000' not in shown


def test_financial_classes_are_separate_and_operational_amounts_remain_useful(client):
    from app.agent.disclosure import minimize, filter_answer
    who = login(client)
    user = auth.authenticate(who['Authorization'])
    data = {'items': [{'kind': 'CREDIT', 'status': 'ACTIVE', 'credit_limit_vnd': 5000000, 'outstanding_vnd': 50000,
        'available_credit_vnd': 4950000, 'transactions': [{'amount_vnd': 50000, 'merchant': 'Notebook'}]}]}
    with get_db().connect() as conn:
        available = minimize(conn, user, 'get_cards', data, {'text': 'How much credit is available on my card?'})['items'][0]
        assert available['available_credit_vnd'] == 4950000
        assert 'outstanding_vnd' not in available and 'credit_limit_vnd' not in available
        debt = minimize(conn, user, 'get_cards', data, {'text': 'What is my card debt?'})['items'][0]
        assert debt['outstanding_vnd'] == 50000 and 'available_credit_vnd' not in debt
        limit = minimize(conn, user, 'get_cards', data, {'text': 'What is my credit card limit?'})['items'][0]
        assert limit['credit_limit_vnd'] == 5000000 and 'outstanding_vnd' not in limit
        history = minimize(conn, user, 'get_cards', data, {'text': 'Show my card purchase history'})['items'][0]
        assert history['transactions'][0]['amount_vnd'] == 50000
        assert 'outstanding_vnd' not in history
        safe = 'Your latest card purchase was 50,000 VND.'
        assert filter_answer(conn, user.id, {'text': 'Show my card purchase history'}, safe) == safe


def test_savings_principal_and_interest_require_relevant_read_intent(client):
    from app.agent.disclosure import minimize, filter_answer
    who = login(client)
    user = auth.authenticate(who['Authorization'])
    data = {'items': [{'status': 'ACTIVE', 'principal_vnd': 1000000, 'projected_interest_vnd': 25000,
        'interest_paid_vnd': 1000, 'events': [{'kind': 'OPEN', 'amount_vnd': 1000000}]}]}
    with get_db().connect() as conn:
        status = minimize(conn, user, 'get_savings', data, {'text': 'Show the status of my savings only'})['items'][0]
        assert status == {'status': 'ACTIVE'}
        principal = minimize(conn, user, 'get_savings', data, {'text': 'How much is my savings principal?'})['items'][0]
        assert principal['principal_vnd'] == 1000000 and 'projected_interest_vnd' not in principal
        interest = minimize(conn, user, 'get_savings', data, {'text': 'How much interest have my savings earned?'})['items'][0]
        assert interest['projected_interest_vnd'] == 25000 and 'principal_vnd' not in interest
        for answer in ('Your savings principal is 1,000,000 VND.', 'Your savings interest is 25,000 VND.', 'Your card debt is fifty thousand dong.', 'Dư nợ thẻ của bạn là 50.000 đồng.', 'Your card debt is 50000.', 'Your card debt is 50k.', 'Your card debt is 50000₫.'):
            assert filter_answer(conn, user.id, {'text': 'Show status only'}, answer) != answer
        safe = 'You can check your card debt in the banking screen.'
        assert filter_answer(conn, user.id, {'text': 'Show status only'}, safe) == safe


def test_spending_read_does_not_authorize_account_card_or_savings_balances(client):
    from app.agent.disclosure import minimize
    who = login(client)
    user = auth.authenticate(who['Authorization'])
    data = {'income_vnd': 70000, 'expense_vnd': 50000, 'net_vnd': 20000, 'total_balance_vnd': 12500000,
        'credit_debt_vnd': 50000, 'savings_principal_vnd': 1000000, 'categories': [{'category': 'food', 'amount_vnd': 50000}]}
    with get_db().connect() as conn:
        result = minimize(conn, user, 'get_spending_summary', data, {'text': 'How much did I spend this month?'})
    assert result['expense_vnd'] == 50000 and result['categories'][0]['amount_vnd'] == 50000
    assert not {'total_balance_vnd', 'credit_debt_vnd', 'savings_principal_vnd'} & result.keys()


@pytest.mark.parametrize('text,expected', [
    ('What is my credit card balance?', 'get_cards'),
    ('How much credit is available on my card?', 'get_cards'),
    ('What is my savings balance?', 'get_savings'),
    ('How much have I saved?', 'get_savings'),
    ('How much interest will my savings earn?', 'get_savings'),
    ('What is my payment account balance and card status?', 'get_account_balance'),
    ('Balance of ACC-ALICE-001, not my credit card', 'get_account_balance'),
    ('Show the status of my cards only', None),
])
def test_financial_read_tool_hint_distinguishes_own_financial_classes(text, expected):
    from app.agent.disclosure import financial_read_tool
    assert financial_read_tool({'text': text}) == expected


def test_payment_balance_before_card_payment_does_not_authorize_debt_or_savings():
    from app.agent.disclosure import financial_classes
    assert financial_classes({'text': 'What is my payment account balance before paying my card?'}) == {'payment_balance'}
    assert financial_classes({'text': 'What is my payment account balance before moving money to savings?'}) == {'payment_balance'}


@pytest.mark.parametrize('answer', ['Your debt is 50,000 VND.', 'You owe 50000.', 'Your debt is fifty thousand dong.'])
def test_generic_debt_wording_cannot_disclose_unrequested_money(client, answer):
    from app.agent.disclosure import filter_answer
    with get_db().connect() as conn:
        intent = {'text': 'Show the status of my cards only'}
        assert filter_answer(conn, 'alice', intent, answer) != answer
        safe = 'Your latest card purchase was 50,000 VND.'
        assert filter_answer(conn, 'alice', {'text': 'Show card purchase history'}, safe) == safe
