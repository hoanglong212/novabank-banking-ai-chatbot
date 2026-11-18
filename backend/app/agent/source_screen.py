"""Classifier signals in a fixed chain; bank policy remains the authority."""
from ..config import provider
from ..faq import fold
from ..guard import inspect_prompt
from . import agent_guard, promptguard


async def classify(text):
    if provider() == 'mock':
        verdict = await agent_guard.classify(text)
        return {**verdict, 'signals': [{'stage': 'explicit_mock', **verdict}]}
    flagged = bool(inspect_prompt(text).reason or agent_guard.JUDGE_STEERING.search(fold(text)))
    signals = [{'stage': 'regex', 'injection': flagged, 'method': 'deterministic'}]
    if flagged:
        return {'injection': True, 'method': 'deterministic', 'signals': signals}
    guarded = await promptguard.classify(text)
    signals.append({'stage': 'prompt_guard_2', **guarded})
    if guarded.get('available') is not True or guarded.get('injection') is not False:
        return {'injection': True, 'method': guarded.get('method', 'unavailable'), 'signals': signals}
    verdict = await agent_guard.classify(text)
    signals.append({'stage': 'qwen', **verdict})
    return {**verdict, 'signals': signals}
