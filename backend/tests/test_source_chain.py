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
