from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def tool(client, token, name, arguments=None):
    return client.post('/api/agent/tools', headers=token, json={'name': name, 'arguments': arguments or {}}).json()


def test_unsolicited_account_details_never_enter_model_but_requested_balance_works(client):
    who = login(client)
    _, _, token = run_for(client, who, 'What are your opening hours?')
    accounts = tool(client, token, 'get_accounts')
    assert accounts['decision'] == 'ALLOW'
    encoded = json.dumps(accounts['result'])
    assert 'balance_vnd' not in encoded and 'ACC-ALICE' not in encoded
    unsolicited = tool(client, token, 'get_account_balance')
    assert (unsolicited['decision'], unsolicited['reason']) == ('DENY', 'READ_INTENT_REQUIRED')
    _, _, token = run_for(client, who, 'What is my balance?')
    own = tool(client, token, 'get_account_balance')
    assert own['decision'] == 'ALLOW' and own['result']['balance_vnd'] > 0


def test_output_blocks_foreign_balances_and_unsolicited_own_details_with_safe_control(client):
    who = login(client)
    with get_db().connect() as conn:
        foreign = conn.execute("SELECT balance_vnd FROM accounts WHERE owner_id='bob'").fetchone()[0]
    _, grant, token = run_for(client, who, 'Hello')
    for text in ('Your account is ACC-ALICE-001.', 'Bob account ACC-BOB-001 is active.', f'Bob balance: {foreign:,} VND.'):
        result = client.post('/api/agent/preview', headers=token, json={'answer': text}).json()['text']
        assert result != text and 'ACC-' not in result and f'{foreign:,}' not in result
    good = 'Welcome. How can I help you today?'
    assert client.post('/api/agent/preview', headers=token, json={'answer': good}).json()['text'] == good
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM security_events WHERE run_id=? AND event='output_filtered'", (grant['run_id'],)).fetchone()[0] >= 3
    _, _, token = run_for(client, who, 'What is my balance?')
    own = tool(client, token, 'get_account_balance')['result']['balance_vnd']
    response = client.post('/api/agent/preview', headers=token, json={'answer': 'Unverified narrative'}).json()['text']
    assert f'{own:,}' in response


def test_foreign_pseudonym_cannot_bypass_output_filter_when_vault_is_restored(client):
    from app.auth_crypto import decrypt_secret
    who = login(client)
    beneficiary(client, who)
    _, grant, token = run_for(client, who, 'Hello')
    with get_db().connect() as conn:
        encrypted = conn.execute('SELECT vault_json FROM agent_runs WHERE id=?', (grant['run_id'],)).fetchone()[0]
        values = json.loads(decrypt_secret(get_db(), encrypted))
        alias = next(key for key, value in values.items() if value == 'ACC-BOB-001')
    shown = client.post('/api/agent/preview', headers=token, json={'answer': 'Account number: ' + alias}).json()['text']
    assert 'ACC-BOB-001' not in shown and alias not in shown
    clean = client.post('/api/agent/preview', headers=token, json={'answer': 'Welcome to NovaBank.'}).json()['text']
    assert clean == 'Welcome to NovaBank.'


def test_support_never_receives_balance_even_when_ticket_quotes_it(client):
    who = login(client)
    ticket = client.post('/api/support/tickets', headers=who, json={'subject': 'Question', 'description': 'My balance is 99000000 VND, why is my card pending?'}).json()
    _, _, token = run_for(client, login(client, 'support'), 'Read ticket ' + ticket['id'])
    result = tool(client, token, 'read_ticket', {'ticket_id': ticket['id']})
    assert result['decision'] == 'ALLOW' and '99000000' not in json.dumps(result['result'])
    assert 'balance' not in json.dumps(result['result'])
    forbidden = tool(client, token, 'get_customer_summary', {'ticket_id': ticket['id']})
    assert forbidden['decision'] == 'DENY' and forbidden['reason'] == 'ROLE_NOT_PERMITTED'
    _, _, token = run_for(client, login(client, 'support'), 'Reply to ' + ticket['id'])
    guessed = tool(client, token, 'propose_ticket_reply', {'ticket_id': ticket['id'], 'body': 'Hello, your balance is 12,500,000 VND.'})
    assert guessed['decision'] == 'DENY' and guessed['reason'] == 'REPLY_PRIVATE_BALANCE'
    safe = tool(client, token, 'propose_ticket_reply', {'ticket_id': ticket['id'], 'body': 'Hello, please check your balance in the account dashboard. Our team will look into your card question.'})
    assert safe['decision'] == 'ALLOW'


def test_nested_alias_from_verified_display_name_is_never_expanded_after_filter(client):
    from tests.test_customer_products import confirm
    who = login(client)
    beneficiary(client, who)
    draft = client.post('/api/customer/profile/change', headers=who, json={
        'field': 'name', 'value': '<ACCOUNT_2>', 'password': 'Alice@2026'})
    assert draft.status_code == 202, draft.text
    assert confirm(client, who, draft.json(), 'nested-alias-name').status_code == 200
    _, _, token = run_for(client, who, 'Hello')
    preview = client.post('/api/agent/preview', headers=token, json={'answer': '<NAME_1>'})
    finished = client.post('/api/agent/finish', headers=token, json={'answer': '<NAME_1>', 'latency_ms': 1})
    assert preview.status_code == finished.status_code == 200
    assert 'ACC-BOB-001' not in preview.json()['text']
    assert 'ACC-BOB-001' not in finished.json()['message']['content']
    # Ordinary named-account balances must still restore their own account alias.
    _, _, token = run_for(client, who, 'What is the balance of ACC-ALICE-001?')
    result = tool(client, token, 'get_account_balance', {'account_id': 'ACC-ALICE-001'})
    assert result['decision'] == 'ALLOW'
    shown = client.post('/api/agent/preview', headers=token, json={'answer': 'Balance'}).json()['text']
    assert 'ACC-ALICE-001' in shown and f'{result["result"]["balance_vnd"]:,}' in shown
