import asyncio
from app.agent import promptguard, agent_guard


def test_prompt_guard_unavailable_denies_without_qwen_fallback_and_clean_signals_allow(monkeypatch):
    from app.agent.source_screen import classify
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    calls = []
    async def missing(text):
        return {'injection': True, 'available': False, 'method': 'unavailable'}
    async def judge(text):
        calls.append(text)
        return {'injection': False, 'method': 'local_model'}
    monkeypatch.setattr(promptguard, 'classify', missing)
    monkeypatch.setattr(agent_guard, 'classify', judge)
    result = asyncio.run(classify('Ordinary salary payment'))
    assert result['injection'] is True and result['method'] == 'unavailable' and not calls
    async def clear(text):
        return {'injection': False, 'available': True, 'method': 'prompt_guard_2'}
    monkeypatch.setattr(promptguard, 'classify', clear)
    result = asyncio.run(classify('Ordinary salary payment'))
    assert result['injection'] is False and len(calls) == 1
    assert [signal['stage'] for signal in result['signals']] == ['regex', 'prompt_guard_2', 'qwen']


def test_model_request_is_shared_with_detector_benchmark():
    request = agent_guard.model_request('Salary payment', 'qwen2.5:7b')
    assert request['model'] == 'qwen2.5:7b'
    assert request['messages'][1]['content'] == '<source>Salary payment</source>'
    assert request['format'] == 'json' and request['stream'] is False
    assert request['options'] == {'temperature': 0, 'num_predict': 40, 'num_ctx': 8192}
    assert 'think' not in request
    assert agent_guard.model_request('Salary', 'qwen3:8b')['think'] is False


def test_only_b_and_d_enable_classifier_layer():
    from app.agent.policy import load
    assert {config: load(config)['layers']['classifier'] for config in 'ABCD'} == {
        'A': False, 'B': True, 'C': False, 'D': True}


def test_qd6_guard_defaults_to_qwen25_independent_of_primary_model(monkeypatch):
    import httpx
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    monkeypatch.setenv('OLLAMA_MODEL', 'qwen3:8b')
    monkeypatch.delenv('GUARD_MODEL', raising=False)
    seen = []
    async def handle(request):
        import json
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={'message': {'content': '{"injection":false}'}})
    original = httpx.AsyncClient
    monkeypatch.setattr(agent_guard.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    result = asyncio.run(agent_guard.classify('Ordinary salary payment'))
    assert result['injection'] is False
    assert seen[0]['model'] == 'qwen2.5:7b'
