import asyncio
import json
import httpx
import pytest


@pytest.mark.parametrize('model', ['qwen2.5:7b', 'qwen3:8b'])
def test_source_classifier_disables_qwen3_thinking_and_keeps_plain_models(monkeypatch, model):
    from app.agent import agent_guard
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    monkeypatch.setenv('GUARD_MODEL', model)
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'message': {'content': '{"injection":false}'}})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(agent_guard.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    result = asyncio.run(agent_guard.classify('Monthly salary payment'))
    assert result['injection'] is False
    assert requests[0]['model'] == model
    if model == 'qwen3:8b':
        assert requests[0].get('think') is False
    else:
        assert 'think' not in requests[0]
