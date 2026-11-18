from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_balance_answer_uses_bank_facts_in_preview_and_final(client):
    who = login(client)
    expected = sum(a['balance_vnd'] for a in client.get('/api/me', headers=who).json()['accounts'])
    _, _, token = run_for(client, who)
    result = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {}})
    assert result.json()['decision'] == 'ALLOW'
    for endpoint in ('preview', 'finish'):
        payload = {'answer': 'Your balance is 123 VND.'}
        if endpoint == 'finish':
            payload['latency_ms'] = 1
        response = client.post('/api/agent/' + endpoint, headers=token, json=payload)
        assert response.status_code == 200
        text = response.json()['text'] if endpoint == 'preview' else response.json()['message']['content']
        assert f'{expected:,} VND' in text
        assert '123 VND' not in text


@pytest.mark.parametrize('answer', ['Your balance is 123 VND.', 'Your balance is twelve million dong.'])
def test_unverified_balance_is_not_displayed(client, answer):
    who = login(client)
    _, _, token = run_for(client, who)
    text = client.post('/api/agent/finish', headers=token, json={'answer': answer, 'latency_ms': 1}).json()['message']['content']
    assert 'have not verified' in text


def test_explicit_account_balance_stays_scoped_to_that_account(client):
    who = login(client)
    account = client.get('/api/me', headers=who).json()['accounts'][0]
    _, _, token = run_for(client, who, 'Balance of account ' + account['id'])
    result = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {'account_id': account['id']}}).json()
    assert result['decision'] == 'ALLOW'
    assert result['result']['balance_vnd'] == account['balance_vnd']
    text = client.post('/api/agent/finish', headers=token, json={'answer': 'Your balance is 123 VND.', 'latency_ms': 1}).json()['message']['content']
    assert account['id'] in text
    assert f'{account["balance_vnd"]:,} VND' in text


def test_default_balance_tool_totals_all_owned_accounts(client):
    who = login(client)
    with get_db().connect() as conn:
        account = conn.execute("SELECT * FROM accounts WHERE owner_id='alice' LIMIT 1").fetchone()
        columns = account.keys()
        extra = dict(account)
        extra.update(id='ACC-ALICE-EXTRA', balance_vnd=765432)
        conn.execute(f"INSERT INTO accounts ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", tuple(extra[c] for c in columns))
    expected = sum(a['balance_vnd'] for a in client.get('/api/me', headers=who).json()['accounts'])
    _, _, token = run_for(client, who)
    result = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {}}).json()
    with get_db().connect() as conn:
        conn.execute("DELETE FROM accounts WHERE id='ACC-ALICE-EXTRA'")
    assert result['result']['balance_vnd'] == expected


@pytest.mark.parametrize(('question', 'tool_name', 'kind', 'field'), [
    ('What is my credit card debt?', 'get_cards', 'cards', 'outstanding_vnd'),
    ('What is my savings balance?', 'get_savings', 'savings', 'principal_vnd'),
])
def test_product_balances_use_verified_bank_values_in_preview_and_final(client, monkeypatch, question, tool_name, kind, field):
    monkeypatch.setenv('ENV', 'lab')
    who, admin = login(client), login(client, 'admin')
    assert client.put('/api/admin/agent-gateway', headers=admin, json={'config': 'C', 'users': ['alice'], 'minutes': 2}).status_code == 200
    items = client.get('/api/products/' + kind, headers=who).json()['items']
    from tests.test_customer_products import confirm
    payload = ({'kind': 'CARD_PURCHASE', 'resource_id': next(row['id'] for row in items if row['kind'] == 'CREDIT'),
                'amount_vnd': 50000, 'label': 'Books'} if kind == 'cards' else
               {'kind': 'OPEN_SAVINGS', 'account_id': 'ACC-ALICE-001', 'amount_vnd': 100000, 'term_months': 3, 'label': 'Trip'})
    action = client.post('/api/products/actions', headers=who, json=payload)
    assert action.status_code == 202
    assert confirm(client, who, action.json(), 'product-balance-proof').status_code == 200
    items = client.get('/api/products/' + kind, headers=who).json()['items']
    expected = sum(row[field] for row in items if row.get('kind') == 'CREDIT' or kind == 'savings' and row['status'] == 'ACTIVE')
    _, _, token = run_for(client, who, question)
    result = client.post('/api/agent/tools', headers=token, json={'name': tool_name, 'arguments': {}})
    assert result.json()['decision'] == 'ALLOW'
    for endpoint in ('preview', 'finish'):
        payload = {'answer': 'The amount is 123 VND.'}
        if endpoint == 'finish':
            payload['latency_ms'] = 1
        response = client.post('/api/agent/' + endpoint, headers=token, json=payload)
        text = response.json()['text'] if endpoint == 'preview' else response.json()['message']['content']
        assert f'{expected:,} VND' in text and '123 VND' not in text


def test_product_balance_without_verified_read_is_not_guessed(client):
    _, _, token = run_for(client, login(client), 'What is my credit card debt?')
    response = client.post('/api/agent/preview', headers=token, json={'answer': 'Your card debt is 123 VND.'})
    assert 'have not verified' in response.json()['text']


def test_actual_paid_savings_interest_is_minimized_and_rendered_when_requested(client, monkeypatch):
    from tests.test_customer_products import confirm
    from app import products
    monkeypatch.setenv('ENV', 'lab')
    who, admin = login(client), login(client, 'admin')
    assert client.put('/api/admin/agent-gateway', headers=admin, json={'config': 'C', 'users': ['alice'], 'minutes': 2}).status_code == 200
    action = client.post('/api/products/actions', headers=who, json={
        'kind': 'OPEN_SAVINGS', 'account_id': 'ACC-ALICE-001', 'amount_vnd': 100000, 'term_months': 3, 'label': 'Trip'}).json()
    assert confirm(client, who, action, 'interest-open').status_code == 200
    saving = client.get('/api/products/savings', headers=who).json()['items'][0]
    from datetime import datetime, timezone
    from types import SimpleNamespace
    monkeypatch.setattr(products, 'datetime', SimpleNamespace(fromtimestamp=lambda *_: datetime(2030, 11, 15, tzinfo=timezone.utc)))
    withdrawal = client.post('/api/products/actions', headers=who, json={'kind': 'WITHDRAW_SAVINGS', 'resource_id': saving['id']}).json()
    assert confirm(client, who, withdrawal, 'interest-close').status_code == 200
    paid = client.get('/api/products/savings', headers=who).json()['items'][0]['interest_paid_vnd']
    assert paid > 0
    _, _, status_token = run_for(client, who, 'Show the status of my savings only')
    hidden = client.post('/api/agent/tools', headers=status_token, json={'name': 'get_savings', 'arguments': {}}).json()['result']
    assert 'interest_paid_vnd' not in json.dumps(hidden)
    _, _, token = run_for(client, who, 'How much interest have my savings earned?')
    result = client.post('/api/agent/tools', headers=token, json={'name': 'get_savings', 'arguments': {}}).json()
    assert result['decision'] == 'ALLOW'
    answer = client.post('/api/agent/preview', headers=token, json={'answer': '123 VND'}).json()['text']
    assert f'Paid savings interest: **{paid:,} VND**.' in answer
