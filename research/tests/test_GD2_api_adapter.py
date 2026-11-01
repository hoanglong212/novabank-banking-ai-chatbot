import importlib
import json
from pathlib import Path
import httpx
import pytest


def adapter_module():
    assert (Path(__file__).parents[1] / 'api_adapter.py').exists(), 'Research API adapter not implemented'
    return importlib.import_module('research.api_adapter')


def config(tmp_path, monkeypatch):
    mod = adapter_module()
    for key in ('RESEARCH_API_KEY', 'RESEARCH_API_BASE_URL', 'RESEARCH_API_MODEL', 'RESEARCH_API_SUPPORTS_SEED'):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / '.env'
    path.write_text('RESEARCH_API_KEY=fixture-private-value\nRESEARCH_API_BASE_URL=https://provider.invalid/v1\nRESEARCH_API_MODEL=snapshot-fixture\n', encoding='utf-8')
    return mod, mod.ApiConfig.from_env(path)


def test_GD2_api_configuration_reads_env_without_printing_secret(tmp_path, monkeypatch):
    mod, cfg = config(tmp_path, monkeypatch)
    assert cfg.api_key == 'fixture-private-value'
    assert 'fixture-private-value' not in repr(cfg)
    monkeypatch.setenv('RESEARCH_API_MODEL', 'process-snapshot')
    assert mod.ApiConfig.from_env(tmp_path / '.env').model == 'process-snapshot'


def test_GD2_api_disabled_by_default_before_any_network(tmp_path, monkeypatch):
    mod, cfg = config(tmp_path, monkeypatch)
    def forbidden(request):
        pytest.fail('A disabled adapter contacted transport')
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(mod.ApiDisabled):
            mod.ApiAdapter(cfg, client=client).complete([{'role': 'user', 'content': 'balance'}])


def test_GD2_api_normalizes_usage_and_tool_calls_offline(tmp_path, monkeypatch):
    mod, cfg = config(tmp_path, monkeypatch)
    def reply(request):
        body = json.loads(request.content)
        assert request.headers['authorization'] == 'Bearer fixture-private-value'
        assert str(request.url) == 'https://provider.invalid/v1/chat/completions'
        assert body['model'] == 'snapshot-fixture' and body['temperature'] == 0
        assert 'seed' not in body  # unsupported must be reported, not assumed
        return httpx.Response(200, json={'id': 'resp-fixture', 'model': 'snapshot-fixture',
            'usage': {'prompt_tokens': 42, 'completion_tokens': 7},
            'choices': [{'finish_reason': 'tool_calls', 'message': {'content': None, 'tool_calls': [
                {'id': 'call-one', 'type': 'function', 'function': {'name': 'get_account_balance', 'arguments': '{}'}}]}}]})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        row = mod.ApiAdapter(cfg, client=client, allow_live=True).complete([{'role': 'user', 'content': 'balance'}], seed=7)
    assert row['input_tokens'] == 42 and row['output_tokens'] == 7
    assert row['message']['tool_calls'][0]['function']['arguments'] == {}
    assert row['seed_requested'] == 7 and row['seed_sent'] is None
    assert row['model_returned'] == 'snapshot-fixture'


@pytest.mark.parametrize('kind', ['http_error', 'missing_usage', 'bad_arguments'])
def test_GD2_api_failures_never_echo_key_or_raw_body(tmp_path, monkeypatch, kind):
    mod, cfg = config(tmp_path, monkeypatch)
    def reply(request):
        if kind == 'http_error':
            return httpx.Response(401, text='fixture-private-value raw response secret')
        data = {'model': 'snapshot-fixture', 'choices': [{'message': {'content': '', 'tool_calls': []}}]}
        if kind == 'bad_arguments':
            data['usage'] = {'prompt_tokens': 1, 'completion_tokens': 2}
            data['choices'][0]['message']['tool_calls'] = [{'function': {'name': 'tool', 'arguments': 'fixture-private-value'}}]
        return httpx.Response(200, json=data)
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        with pytest.raises(mod.ApiAdapterError) as err:
            mod.ApiAdapter(cfg, client=client, allow_live=True).complete([{'role': 'user', 'content': 'hi'}])
    assert 'fixture-private-value' not in str(err.value)
    assert err.value.__suppress_context__


def test_GD2_api_placeholder_and_insecure_url_rejected_without_network(tmp_path, monkeypatch):
    mod, cfg = config(tmp_path, monkeypatch)
    for url, model in [('http://provider.invalid/v1', 'm'), ('https://key@provider.invalid/v1', 'm'),
                       ('https://provider.invalid/v1?key=secret', 'm'), ('https://provider.invalid/v1', '<API_MODEL>')]:
        with pytest.raises(ValueError):
            mod.ApiConfig(base_url=url, model=model, api_key='fixture').validate()
