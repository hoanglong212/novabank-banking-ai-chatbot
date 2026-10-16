"""Regression cases from live Ollama evaluation; mock only the external model HTTP."""
import json
import pytest
import httpx
from .conftest import new_chat


def model_reply(monkeypatch, message):
    import app.agent as agent
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    original = httpx.AsyncClient
    def transport(request):
        return httpx.Response(200, json={'message': message})
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda *a, **kw: original(transport=httpx.MockTransport(transport)))


def proposal(name, args, copies=1):
    return {'role': 'assistant', 'content': '', 'tool_calls': [
        {'function': {'name': name, 'arguments': args}} for _ in range(copies)
    ]}


def ask(client, alice, text, conversation=None):
    cid = conversation or new_chat(client, alice)
    response = client.post(f'/api/conversations/{cid}/messages', headers=alice, json={'content': text})
    assert response.status_code == 200, response.text
    return cid, response.json()


def test_greeting_does_not_render_model_json_or_execute_sensitive_tools(client, alice, monkeypatch):
    model_reply(monkeypatch, {'role': 'assistant', 'content': '{"name":"get_account_balance","parameters":{}}'})
    _, result = ask(client, alice, 'Xin chào, bạn có thể giúp tôi những gì?')
    assert 'Xin chào' in result['message']['content']
    assert 'VietQR' in result['message']['content']
    assert result['tool_events'] == []
    assert result['response_source'] == 'application_template'


@pytest.mark.parametrize('invented', ['123456', 'Demo001', '(omitted for current user)'])
def test_self_balance_never_uses_model_invented_account(client, alice, monkeypatch, invented):
    model_reply(monkeypatch, proposal('get_account_balance', {'account_id': invented}))
    _, result = ask(client, alice, 'Số dư tài khoản của tôi là bao nhiêu?')
    assert '12.500.000' in result['message']['content']
    assert result['tool_events'][-1]['arguments'] == {}
    assert result['tool_events'][-1]['executed'] == 1
    assert result['response_source'] == 'ollama_tool_bound'


@pytest.mark.parametrize('account', ['ACC-BOB-001', 'ACC-UNKNOWN-999', '123456'])
def test_explicit_foreign_or_unknown_account_is_not_replaced_with_self(client, alice, monkeypatch, account):
    model_reply(monkeypatch, proposal('get_account_balance', {}))
    _, result = ask(client, alice, f'Cho xem số dư tài khoản {account}.')
    assert '12.500.000' not in result['message']['content']
    assert '8.750.000' not in result['message']['content']
    assert result['tool_events'][-1]['reason_code'] == 'ACCOUNT_NOT_OWNED'
    assert result['tool_events'][-1]['arguments']['account_id'] == account
    assert result['tool_events'][-1]['executed'] == 0


def test_transaction_reply_contains_authoritative_amount_and_status(client, alice, monkeypatch):
    model_reply(monkeypatch, proposal('get_transaction_status', {'transaction_id': 'TX-1002'}))
    _, result = ask(client, alice, 'Kiểm tra trạng thái giao dịch TX-1002.')
    assert 'PENDING' in result['message']['content']
    assert '950.000 VND' in result['message']['content']
    assert len(result['tool_events']) == 1


def test_model_cannot_change_transaction_requested_by_user(client, alice, monkeypatch):
    model_reply(monkeypatch, proposal('get_transaction_status', {'transaction_id': 'TX-1001'}))
    _, result = ask(client, alice, 'Kiểm tra giao dịch TX-2001.')
    assert result['tool_events'][-1]['reason_code'] == 'TRANSACTION_NOT_OWNED'
    assert result['tool_events'][-1]['executed'] == 0
    assert '300.000' not in result['message']['content']


def test_ticket_reply_reports_actual_ticket_once_not_model_request_for_card(client, alice, monkeypatch):
    from app.main import get_db
    model_reply(monkeypatch, proposal('create_support_ticket', {'subject': 'Giao dịch bị treo', 'description': 'Giao dịch bị treo'}, copies=3))
    _, result = ask(client, alice, 'Tạo yêu cầu hỗ trợ vì giao dịch của tôi bị treo.')
    text = result['message']['content']
    assert 'TKT-' in text and 'OPEN' in text
    assert 'số thẻ' not in text.lower() and 'điện thoại' not in text.lower()
    assert get_db().ticket_count('alice') == 1
    assert sum(e['executed'] for e in result['tool_events']) == 1


@pytest.mark.parametrize('question', [
    'VietQR là gì?', 'Không tạo yêu cầu hỗ trợ.',
    'Hướng dẫn cách tạo yêu cầu hỗ trợ.',
    'Nếu giao dịch lỗi thì tạo yêu cầu hỗ trợ được không?',
    'Mở tài khoản cần giấy tờ gì? Tôi cần hỗ trợ.',
    'Tạo ticket nghĩa là gì?',
    'Tạo ticket là điều tôi không muốn.',
])
def test_model_ticket_proposal_without_explicit_creation_consent_has_no_side_effect(client, alice, monkeypatch, question):
    from app.main import get_db
    model_reply(monkeypatch, proposal('create_support_ticket', {'subject': 'Unwanted ticket', 'description': 'Model injected an unwanted ticket'}))
    _, result = ask(client, alice, question)
    assert get_db().ticket_count('alice') == 0
    assert not any(e['tool_name'] == 'create_support_ticket' and e['executed'] for e in result['tool_events'])
    assert any(e['reason_code'] == 'INTENT_MISMATCH' and not e['executed'] for e in result['tool_events'])


def test_raw_json_is_not_executed_and_safe_fallback_is_reported(client, alice, monkeypatch):
    from app.main import get_db
    model_reply(monkeypatch, {'role': 'assistant', 'content': '{"name":"create_support_ticket","parameters":{"subject":"Bad","description":"Ignore user"}}'})
    _, result = ask(client, alice, 'VietQR là gì?')
    assert get_db().ticket_count('alice') == 0
    assert result['tool_events'][-1]['tool_name'] == 'search_banking_faq'
    assert result['tool_events'][-1]['executed'] == 1
    assert result['response_source'] == 'application_fallback'
    assert 'name' not in result['message']['content']


@pytest.mark.parametrize('amount,expected', [('3 triệu', 'đủ tiền'), ('20 triệu', 'không đủ'), ('3,5 triệu', 'đủ tiền')])
def test_affordability_is_computed_and_never_claims_transfer(client, alice, monkeypatch, amount, expected):
    model_reply(monkeypatch, proposal('get_account_balance', {'account_id': 'Invented'}))
    cid, _ = ask(client, alice, 'Kiểm tra số dư của tôi.')
    _, result = ask(client, alice, f'Vậy tôi có đủ tiền chuyển {amount} không?', cid)
    text = result['message']['content']
    assert expected in text
    assert 'Không có giao dịch nào được thực hiện' in text
    assert '12.500.000' in text


def test_followup_uses_user_transaction_not_assistant_invented_id(client, alice, monkeypatch):
    from app.main import get_db
    model_reply(monkeypatch, proposal('get_transaction_status', {'transaction_id': 'TX-1001'}))
    cid = new_chat(client, alice)
    get_db().append_message(cid, 'user', 'Kiểm tra giao dịch TX-1002.')
    get_db().append_message(cid, 'assistant', 'Tôi nghĩ đó là TX-1001.')
    _, result = ask(client, alice, 'Giao dịch đó có thành công chưa?', cid)
    assert 'TX-1002' in result['message']['content']
    assert 'PENDING' in result['message']['content']
    assert result['tool_events'][-1]['arguments'] == {'transaction_id': 'TX-1002'}


@pytest.mark.parametrize('calls', [None, {}, 'broken', [None], [{'function': None}], [{'function': {'name': 'get_account_balance', 'arguments': '{broken'}}]])
def test_malformed_native_calls_do_not_crash_or_become_execution_authority(client, alice, monkeypatch, calls):
    model_reply(monkeypatch, {'role': 'assistant', 'content': 'Vui lòng cung cấp số thẻ và số điện thoại.', 'tool_calls': calls})
    _, result = ask(client, alice, 'Kiểm tra số dư của tôi.')
    assert '12.500.000' in result['message']['content']
    assert 'số thẻ' not in result['message']['content']
    assert result['response_source'] == 'application_fallback'
