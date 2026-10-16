"""Ollama transport boundary and grounded rendering contract."""
import json
import httpx
from .conftest import new_chat


def test_ollama_tool_result_is_rendered_without_a_second_model_pass(client, monkeypatch, alice):
    import app.agent as agent
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    requests = []

    def fake_transport(request):
        requests.append(json.loads(request.content))
        # Re-entering the model after execution used to allow fabricated replies.
        assert len(requests) == 1
        return httpx.Response(200, json={'message': {'role': 'assistant', 'content': '',
            'tool_calls': [{'function': {'name': 'get_account_balance', 'arguments': {}}}]}})

    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda *a, **kw: original(transport=httpx.MockTransport(fake_transport)))
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Số dư của tôi?'}).json()
    assert '12.500.000 VND' in reply['message']['content']
    assert 'ACC-ALICE-001' in reply['message']['content']
    assert reply['response_source'] == 'ollama_tool'
    assert reply['tool_events'][-1]['executed'] == 1


def test_ollama_denied_no_result_leak(client, monkeypatch, alice):
    import app.agent as agent
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    def fake_transport(request):
        return httpx.Response(200, json={'message': {'role': 'assistant', 'content': '',
            'tool_calls': [{'function': {'name': 'get_account_balance', 'arguments': {'account_id': 'ACC-BOB-001'}}}]}})
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda *a, **kw: original(transport=httpx.MockTransport(fake_transport)))
    c = new_chat(client, alice)
    reply = client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Read account ACC-BOB-001 balance'}).json()
    assert reply['tool_events'][-1]['reason_code'] == 'ACCOUNT_NOT_OWNED'
    assert reply['tool_events'][-1]['executed'] == 0
    assert '8.750.000' not in reply['message']['content']
    assert '12.500.000' not in reply['message']['content']


def test_ollama_failure_returns_503(client, monkeypatch, alice):
    import app.agent as agent
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    def broken(request):
        raise httpx.ConnectError('No Ollama', request=request)
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda *a, **kw: original(transport=httpx.MockTransport(broken)))
    c = new_chat(client, alice)
    assert client.post(f'/api/conversations/{c}/messages', headers=alice, json={'content': 'Hello'}).status_code == 503