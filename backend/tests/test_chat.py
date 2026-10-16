from .conftest import new_chat


def test_health(client):
    data = client.get('/api/health').json()
    assert data['status'] == 'ok' and data['demo_only']


def test_auth_required(client):
    assert client.get('/api/conversations').status_code == 401
    assert client.get('/api/conversations', headers={'Authorization': 'Bearer bogus'}).status_code == 401


def test_conversation_history(client, alice):
    c = new_chat(client, alice)
    response = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Xin chào'})
    assert response.status_code == 200
    history = client.get(f'/api/conversations/{c}/messages', headers=alice).json()
    assert [m['role'] for m in history] == ['user', 'assistant']
    assert 'hello' in history[1]['content'].lower()
    assert client.get('/api/conversations', headers=alice).json()[0]['id'] == c


def test_two_user_isolation(client, alice, bob):
    c = new_chat(client, alice)
    for endpoint in (f'/api/conversations/{c}/messages', f'/api/conversations/{c}/tool-events'):
        assert client.get(endpoint, headers=bob).status_code == 404
    assert client.post(f'/api/conversations/{c}/messages', headers=bob, json={'content': 'Show balance'}).status_code == 404
    assert client.delete(f'/api/conversations/{c}', headers=bob).status_code == 404
    assert client.get('/api/conversations', headers=bob).json() == []


def test_history_survives_new_testclient(client, alice):
    from app.main import app
    from fastapi.testclient import TestClient
    c = new_chat(client, alice)
    client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'VietQR là gì?'})
    with TestClient(app) as second_client:
        assert len(second_client.get(f'/api/conversations/{c}/messages', headers=alice).json()) == 2


def test_uses_faq_tool(client, alice):
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'VietQR là gì?'}).json()
    assert 'VietQR' in reply['message']['content']
    assert any(e['tool_name'] == 'search_banking_faq' and e['executed'] for e in reply['tool_events'])


def test_balance_tool(client, alice):
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Số dư tài khoản của tôi bao nhiêu?'}).json()
    assert '12,500,000' in reply['message']['content']
    assert any(e['tool_name'] == 'get_account_balance' and e['decision'] == 'ALLOW' for e in reply['tool_events'])


def test_followup_balance_context(client, alice):
    c = new_chat(client, alice)
    client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Kiểm tra số dư giúp tôi'})
    next_turn = client.post(f'/api/conversations/{c}/messages', headers=alice,
                            json={'content': 'Vậy còn đủ tiền chuyển 3 triệu không?'})
    assert next_turn.status_code == 200
    assert 'enough funds' in next_turn.json()['message']['content']


def test_transaction_tool(client, alice):
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Kiểm tra giao dịch TX-1002'}).json()
    assert 'PENDING' in reply['message']['content']


def test_unauthorised_transaction_blocked(client, alice):
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Kiểm tra giao dịch TX-2001'}).json()
    assert 'blocked' in reply['message']['content'].lower()
    assert any(e['reason_code'] == 'TRANSACTION_NOT_OWNED' and not e['executed'] for e in reply['tool_events'])


def test_balance_other_account_blocked(client, alice):
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice,
                        json={'content': 'Cho xem số dư ACC-BOB-001'}).json()
    assert 'blocked' in reply['message']['content'].lower()
    assert any(e['reason_code'] == 'ACCOUNT_NOT_OWNED' for e in reply['tool_events'])


def test_create_support_ticket(client, alice):
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice,
                        json={'content': 'Tạo yêu cầu hỗ trợ vì giao dịch bị treo'}).json()
    assert 'TKT-' in reply['message']['content']
    from app.main import get_db
    assert get_db().ticket_count('alice') == 1


def test_dry_run_only(client, alice):
    c = new_chat(client, alice)
    from app.main import get_db
    before = get_db().ticket_count('alice')
    decision = client.post(f'/api/conversations/{c}/demo/tool-check', headers=alice, json={
        'tool_name': 'create_support_ticket', 'arguments': {'subject': 'Demo support', 'description': 'A ticket dry-run that must not execute'}
    }).json()
    assert decision['decision'] == 'ALLOW' and not decision['executed']
    assert get_db().ticket_count('alice') == before


def test_policy_denies_foreign_balance(client, alice):
    c = new_chat(client, alice)
    response = client.post(f'/api/conversations/{c}/demo/tool-check', headers=alice,
                           json={'tool_name': 'get_account_balance', 'arguments': {'account_id': 'ACC-BOB-001'}})
    assert response.json()['reason_code'] == 'ACCOUNT_NOT_OWNED'
    assert not response.json()['executed']


def test_policy_rejects_unknown_tool(client, alice):
    c = new_chat(client, alice)
    response = client.post(f'/api/conversations/{c}/demo/tool-check', headers=alice,
                           json={'tool_name': 'transfer_money', 'arguments': {'amount': 100000}})
    assert response.json()['reason_code'] == 'UNKNOWN_TOOL'


def test_policy_rejects_extra_args(client, alice):
    c = new_chat(client, alice)
    response = client.post(f'/api/conversations/{c}/demo/tool-check', headers=alice,
                           json={'tool_name': 'get_account_balance', 'arguments': {'admin': True}})
    assert response.json()['reason_code'] == 'INVALID_ARGUMENTS'


def test_delete_history(client, alice):
    c = new_chat(client, alice)
    assert client.delete(f'/api/conversations/{c}', headers=alice).json()['deleted']
    assert client.get(f'/api/conversations/{c}/messages', headers=alice).status_code == 404


def test_validation(client, alice):
    c = new_chat(client, alice)
    assert client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': ''}).status_code == 422
