import importlib
import json
from pathlib import Path
import httpx
import pytest
from research import engine, scenarios


class FakeSandbox:
    def reset(self):
        pass

    def call(self, *args):
        return {'decision': 'ALLOW'}

    def evidence(self):
        return {'ledger_balanced': True}


def test_GD2_explicit_generation_settings_are_sent_and_recorded():
    seen = []
    def reply(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={'message': {'content': ''}, 'prompt_eval_count': 10, 'eval_count': 2})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        row = engine.run_case(client, 'http://localhost:11434', FakeSandbox(), scenarios.legitimate()[0],
                              'test', 'baseline', 0, temperature=0, seed=73)
    assert seen[0]['options']['temperature'] == 0
    assert seen[0]['options']['seed'] == row['seed'] == 73
    assert row['temperature'] == 0
    assert row['input_tokens'] == 10 and row['output_tokens'] == 2


def pilot_module():
    assert (Path(__file__).parents[1] / 'pilot.py').exists(), 'GD2 pilot not implemented'
    return importlib.import_module('research.pilot')


def test_GD2_pilot_has_exactly_seven_vectors_and_five_distinct_utility_tasks():
    pilot = pilot_module()
    cases = pilot.selected_cases()
    attacks = [c for c in cases if c['kind'] == 'attack']
    utility = [c for c in cases if c['kind'] == 'legitimate']
    assert len(attacks) == 7 and {c['vector'] for c in attacks} == set(scenarios.VECTORS)
    assert all(c['id'].endswith('-01') for c in attacks)
    assert len(utility) == 5
    assert len({c['expected_tool'] for c in utility}) == 5


def test_GD2_costs_keep_cached_classifier_overhead_visible():
    pilot = pilot_module()
    rows = [dict(model='m', profile='defended', kind='attack', wall_ms=100, latency_ms=80,
                 input_tokens=0, output_tokens=0, model_invoked=False, error=None,
                 classifier_charged=True, classifier={'latency_ms': 200, 'input_tokens': 20, 'output_tokens': 3})]
    group = pilot.summarize(rows)[0]
    assert group['mean_wall_ms'] == 100
    assert group['mean_logical_total_ms'] == 300
    assert group['mean_main_tokens'] == 0
    assert group['mean_logical_total_tokens'] == 23
    assert group['model_invocations'] == 0


@pytest.mark.parametrize('url', ['https://remote.example', 'http://127.0.0.1:11434@remote.example', 'http://localhost:11434/?token=x'])
def test_GD2_local_pilot_rejects_remote_or_credentialed_endpoints(url):
    with pytest.raises(ValueError):
        pilot_module().validate_local_url(url)
