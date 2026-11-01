"""Bounded GĐ2 pilot, not the official study. Raw artifacts stay gitignored."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time
from urllib.parse import urlsplit
import uuid
import httpx
from .engine import classify, run_case
from .sandbox import ROOT, Sandbox
from .scenarios import attacks, legitimate, VECTORS

MODELS = ('qwen2.5:7b', 'llama3.1:8b')
PROFILES = ('naive', 'baseline', 'defended')
SEED = 20261101


def selected_cases():
    attack_set = [next(c for c in attacks() if c['id'] == f'{v}-01') for v in VECTORS]
    utility = [next(c for c in legitimate() if c['id'] == f'legit-{g}-01')
               for g in ('balance', 'history', 'status', 'policy', 'transfer')]
    return attack_set + utility


def validate_local_url(value):
    url = urlsplit(value)
    if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1')
            or url.username or url.password or url.query or url.fragment or url.path not in ('', '/')):
        raise ValueError('Pilot accepts only a local Ollama endpoint without credentials/query/path')
    return value.rstrip('/')


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['model'], row['profile'], row['kind'])].append(row)
    result = []
    for (model, profile, kind), items in sorted(groups.items()):
        def classifier(row, field):
            return row['classifier'][field] if row.get('classifier_charged') else 0
        total_ms = [r['wall_ms'] + classifier(r, 'latency_ms') for r in items]
        tokens_known = all(r.get('input_tokens') is not None and r.get('output_tokens') is not None for r in items)
        result.append({'model': model, 'profile': profile, 'kind': kind, 'n': len(items),
            'errors': sum(bool(r['error']) for r in items), 'model_invocations': sum(r['model_invoked'] for r in items),
            'mean_wall_ms': round(statistics.mean(r['wall_ms'] for r in items), 2),
            'median_wall_ms': round(statistics.median(r['wall_ms'] for r in items), 2),
            'mean_logical_total_ms': round(statistics.mean(total_ms), 2),
            'median_logical_total_ms': round(statistics.median(total_ms), 2),
            'mean_input_tokens': round(statistics.mean(r['input_tokens'] for r in items), 2) if tokens_known else None,
            'mean_output_tokens': round(statistics.mean(r['output_tokens'] for r in items), 2) if tokens_known else None,
            'mean_main_tokens': round(statistics.mean(r['input_tokens'] + r['output_tokens'] for r in items), 2) if tokens_known else None,
            'mean_logical_total_tokens': round(statistics.mean(r['input_tokens'] + r['output_tokens'] +
                classifier(r, 'input_tokens') + classifier(r, 'output_tokens') for r in items), 2) if tokens_known else None})
    return result


class MeasuredClient:
    """Capture response counters without persisting request headers or transport errors."""
    def __init__(self, client):
        self.client = client
        self.observations = []

    def post(self, *args, **kwargs):
        response = self.client.post(*args, **kwargs)
        response.raise_for_status()
        data = response.json()
        usage = {k: data.get(k) for k in ('prompt_eval_count', 'eval_count', 'total_duration', 'load_duration',
                                         'prompt_eval_duration', 'eval_duration', 'done_reason')}
        self.observations.append(usage)
        if any(type(usage[k]) is not int or usage[k] < 0 for k in ('prompt_eval_count', 'eval_count')):
            raise ValueError('Missing or invalid model usage')
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', choices=MODELS, default=list(MODELS))
    args = parser.parse_args()
    models = list(dict.fromkeys(args.models))
    base = validate_local_url(os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434'))
    started = time.perf_counter()
    with httpx.Client(timeout=90, trust_env=False, follow_redirects=False) as client:
        response = client.get(base + '/api/tags'); response.raise_for_status()
        available = {item['name']: item for item in response.json()['models']}
        required = set(models) | {'qwen2.5:7b'}
        if not required.issubset(available):
            raise RuntimeError('Required local models are missing; this runner never downloads models')
        directory = ROOT / '.local/research' / ('pilot-gd2-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
        directory.mkdir(parents=True)
        def save(name, value):
            (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        cases = selected_cases()
        save('dataset.json', cases)
        metadata = {'phase': 'GD2_PILOT_NOT_OFFICIAL', 'models': models, 'expected': 36 * len(models),
            'seed': SEED, 'temperature': 0, 'profiles': PROFILES, 'num_ctx': 4096, 'num_predict': 160,
            'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'code_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
            'protocol_sha256': hashlib.sha256((ROOT / 'docs/research/PROTOCOL.md').read_bytes()).hexdigest(),
            'source_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in ('research/pilot.py', 'research/engine.py', 'research/scenarios.py', 'research/sandbox.py')},
            'model_metadata': {m: available[m] for m in required}, 'ollama_version': client.get(base + '/api/version').json(),
            'platform': platform.platform(), 'python': platform.python_version(),
            'trace_origin': 'legacy_research_engine', 'agent_run_id': None,
            'utility_definition': 'legacy_tool_selection_only',
            'limitations': ['SQL lab_sources ingestion, not real banking API poisoning', 'One native model decision, not a full agent conversation',
                           'All selected attacks share misdirect_transfer goal', 'Cached Qwen classifier; physical and logical costs differ',
                           'Pilot cannot verify AI-14/PI-05/PI-06 or rank defenses']}
        save('metadata.json', metadata)
        print('Pilot output:', directory, flush=True)
        sandbox = Sandbox(directory / 'sandbox')
        measured = MeasuredClient(client)
        cache = {}
        for case in cases:
            if case['kind'] == 'attack' and case['vector'] != 'direct':
                cache[case['id']] = classify(measured, base, case['payload'], seed=SEED)
                cache[case['id']]['ollama_metrics'] = measured.observations[-1]
        save('classifier.json', cache)
        rows = []
        try:
            with (directory / 'results.jsonl').open('w', encoding='utf-8') as output:
                for model in models:
                    for profile in PROFILES:
                        for case in cases:
                            measured.observations.clear()
                            case_start = time.perf_counter()
                            row = run_case(measured, base, sandbox, case, model, profile, 0,
                                           cache.get(case['id']), temperature=0, seed=SEED)
                            row.update(wall_ms=round((time.perf_counter() - case_start) * 1000, 2),
                                       observation_id=uuid.uuid4().hex, trace_id=None, agent_run_id=None,
                                       trace_origin='legacy_research_engine', phase='GD2_PILOT_NOT_OFFICIAL',
                                       model_digest=available[model]['digest'], ollama_metrics=measured.observations[:])
                            row['classifier_charged'] = (profile == 'defended' and case['kind'] == 'attack'
                                and case['vector'] != 'direct' and not (case['vector'] == 'memory_context' and case['memory_owner'] != 'alice'))
                            if row['error']:
                                row['input_tokens'] = row['output_tokens'] = None  # unknown, not zero-cost
                            rows.append(row)
                            output.write(json.dumps(row, ensure_ascii=False) + '\n'); output.flush()
                            print(f"{len(rows)}/{metadata['expected']} {model} {profile} {case['id']} {row['wall_ms']/1000:.2f}s error={row['error']}", flush=True)
        finally:
            result = {**metadata, 'completed': len(rows), 'errors': sum(bool(r['error']) for r in rows),
                'elapsed_seconds': round(time.perf_counter() - started, 3), 'metrics': summarize(rows),
                'classifier_physical_calls': len(cache),
                'classifier_physical_ms': sum(c['latency_ms'] for c in cache.values()),
                'classifier_physical_tokens': sum(c['input_tokens'] + c['output_tokens'] for c in cache.values()),
                'ledger_balanced': all(r['sandbox']['ledger_balanced'] for r in rows),
                'status': 'COMPLETED' if len(rows) == metadata['expected'] else 'INTERRUPTED'}
            save('summary.json', result)
        return 0 if not result['errors'] and result['ledger_balanced'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
