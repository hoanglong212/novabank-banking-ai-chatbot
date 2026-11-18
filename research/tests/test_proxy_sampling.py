import pytest


def primary(**options):
    return {'model': 'qwen2.5:7b', 'options': options,
            'messages': [{'role': 'system', 'content': 'You are Nova, ...'}, {'role': 'user', 'content': 'hi'}]}


def test_sampling_override_applies_only_to_primary_chat_when_registered():
    from research.week8_proxy import apply_sampling
    env = {'W8_SAMPLING_TEMPERATURE': '0.7', 'W8_SAMPLING_SEED': '2026111501'}
    changed = apply_sampling('api/chat', primary(temperature=0, num_ctx=8192), env)
    assert changed['options'] == {'temperature': 0.7, 'seed': 2026111501, 'num_ctx': 8192}
    guard = {'model': 'qwen2.5:7b', 'options': {'temperature': 0}, 'messages': [{'role': 'system', 'content': 'Classify'}]}
    assert apply_sampling('api/chat', guard, env) == guard
    assert apply_sampling('api/embed', primary(temperature=0), env) == primary(temperature=0)


def test_sampling_override_is_inert_without_registration_and_rejects_bad_values():
    from research.week8_proxy import apply_sampling
    assert apply_sampling('api/chat', primary(temperature=0), {}) == primary(temperature=0)
    for bad in ({'W8_SAMPLING_TEMPERATURE': 'nan', 'W8_SAMPLING_SEED': '1'},
                {'W8_SAMPLING_TEMPERATURE': '0.7'}, {'W8_SAMPLING_TEMPERATURE': '3', 'W8_SAMPLING_SEED': '1'}):
        with pytest.raises(ValueError):
            apply_sampling('api/chat', primary(temperature=0), bad)


def test_default_harness_environment_keeps_primary_temperature_zero():
    from research.week8_proxy import apply_sampling
    from research.week8_runtime import sampling_env
    inherited = {'PATH': 'x', 'W8_SAMPLING_TEMPERATURE': '0.7', 'W8_SAMPLING_SEED': '7'}
    env = sampling_env(inherited)
    assert 'W8_SAMPLING_TEMPERATURE' not in env and 'W8_SAMPLING_SEED' not in env and env['PATH'] == 'x'
    sent = apply_sampling('api/chat', primary(temperature=0), env)
    assert sent['options']['temperature'] == 0 and 'seed' not in sent['options']
    enabled = sampling_env(inherited, {'temperature': 0.7, 'seed': 2026111501})
    assert apply_sampling('api/chat', primary(temperature=0), enabled)['options'] == {'temperature': 0.7, 'seed': 2026111501}
