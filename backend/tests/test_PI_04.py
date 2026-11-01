"""Small mocked matrix through the actual writer; not a PI-05/06 experiment."""
from tests.acceptance_helpers import ROOT
from pathlib import Path
import json
import sys
import httpx
from research import run, sandbox, scenarios


def test_PI_04_each_matrix_tuple_persists_result_and_trace_even_model_error(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(sandbox, 'ROOT', tmp_path)
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research/engine.py').write_bytes((ROOT / 'research/engine.py').read_bytes())
    attack_set = scenarios.attacks()[:2]
    legit_set = scenarios.legitimate()[:1]
    monkeypatch.setattr(run, 'attacks', lambda: attack_set)
    monkeypatch.setattr(run, 'legitimate', lambda: legit_set)
    monkeypatch.setattr(sys, 'argv', ['research.run','--models','mock-a','mock-b','--repetitions','2','--utility-repetitions','1'])
    original = httpx.Client
    model_calls = 0
    def transport(request):
        nonlocal model_calls
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models':[{'name':m} for m in ('mock-a','mock-b','qwen2.5:7b')]})
        body = json.loads(request.content)
        if body.get('format'):
            return httpx.Response(200,json={'message':{'content':'{"injection":false}'}})
        model_calls += 1
        if model_calls == 5:
            return httpx.Response(503, json={'error':'controlled model outage'})
        return httpx.Response(200,json={'message':{'content':'Mock transport only','tool_calls':[
            {'function':{'name':'get_account_balance','arguments':{}}}]},'prompt_eval_count':11,'eval_count':7})
    monkeypatch.setattr(run.httpx, 'Client', lambda **kw: original(transport=httpx.MockTransport(transport), **kw))
    assert run.main() == 0
    directory = tmp_path / '.local/research' / json.loads((tmp_path / '.local/research/latest.json').read_text())['id']
    records = [json.loads(line) for line in (directory / 'results.jsonl').read_text(encoding='utf-8').splitlines()]
    expected = {(model,profile,case['id'],rep) for model in ('mock-a','mock-b') for profile in ('naive','baseline','defended')
                for case in attack_set+legit_set for rep in range(2 if case['kind']=='attack' else 1)}
    assert len(records) == len(expected) == 30
    assert {(r['model'],r['profile'],r['scenario_id'],r['repetition']) for r in records} == expected
    assert json.loads((directory / 'results.json').read_text(encoding='utf-8')) == records
    assert sum(bool(r['error']) for r in records) == 1
    for row in records:
        assert row['latency_ms'] >= 0 and row['sandbox']['ledger_balanced']
        assert 'raw_model_answer' in row and 'security_events' in row and 'tool_calls' in row
        if not row['error']:
            assert row['input_tokens'] == 11 and row['output_tokens'] == 7
            assert row['tool_calls'] and all('decision' in c and 'arguments' in c for c in row['tool_calls'])
    summary = json.loads((directory / 'summary.json').read_text())
    assert summary['status'] == 'COMPLETED' and summary['expected'] == summary['completed'] == 30
    assert sum(m['errors'] for m in summary['metrics']) == 1
