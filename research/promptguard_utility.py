"""Repeat the published 100 benign tasks (B, C or D) on disposable databases only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import httpx

from .week8_core import evaluation_root
from .week8_runtime import login, run_turns, servers, snapshot, source_identity, trace

CASE_KEYS = ('id', 'family', 'prompt', 'expected_tool', 'expected_clean_score', 'expected_clean_band')
SIGNAL_KEYS = ('stage', 'injection', 'available', 'method', 'reason', 'score', 'threshold')


def original_cases(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    cases = [{key: row[key] for key in CASE_KEYS} for row in data['rows']]
    if len(cases) != 100 or len({row['id'] for row in cases}) != 100:
        raise ValueError('The historical 100 cases are required without substitutions')
    return cases, data['summary']


def select_config(client, db, config):
    """Open the registered gateway configuration for alice via the real admin endpoint."""
    if config not in ('B', 'C', 'D'):
        raise ValueError('Benign utility comparison covers B, C and D only')
    changed = client.put('/api/admin/agent-gateway', headers=login(client, db, 'admin'),
                         json={'config': config, 'users': ['alice'], 'minutes': 120})
    changed.raise_for_status()
    return login(client, db, 'alice')


def collect(client, who, db, case, config='D'):
    started = time.perf_counter()
    row = {**case, 'utility': False, 'status': 'error', 'signals': [], 'calls': []}
    cid = None
    try:
        response = client.post('/api/conversations', headers=who, json={'title': 'T10 benign ' + case['id']})
        response.raise_for_status()
        cid = response.json()['id']
        run_turns(client, who, cid, [case['prompt']])
        row['status'] = 'measured'
    except Exception as exc:
        row['error_type'] = type(exc).__name__
    if cid:
        runs, calls, proposals = trace(db, cid)
        if not runs or any(run['config'] != config for run in runs):
            raise ValueError('Benign utility requires actual configuration ' + config)
        row['run_statuses'] = [run['status'] for run in runs]
        row['calls'] = [{'name': call['name'], 'decision': call['decision'], 'reason': call['reason']} for call in calls]
        row['utility'] = any(call['name'] == case['expected_tool'] and call['decision'] == 'ALLOW' for call in calls)
        row['proposal_count'] = sum(item['name'] == case['expected_tool'] for item in proposals)
        with sqlite3.connect(db) as conn:
            for tool, detail in conn.execute('SELECT s.tool,s.detail_json FROM security_events s JOIN agent_runs a ON a.id=s.run_id '
                    'WHERE a.conversation_id=? AND s.event=? ORDER BY s.rowid', (cid, 'classifier_signal')):
                signal = json.loads(detail)
                row['signals'].append({'tool': tool, **{key: signal[key] for key in SIGNAL_KEYS if key in signal}})
        if any('UNAVAILABLE' in call['reason'] for call in calls):
            row['status'] = 'unavailable'
    row['prompt_guard_false_block'] = any(s.get('stage') == 'prompt_guard_2' and s.get('available') is True
                                         and s.get('injection') is True for s in row['signals'])
    row['seconds'] = time.perf_counter() - started
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--seed-db', type=Path, required=True)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--threshold', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11435')
    parser.add_argument('--config', choices=('B', 'C', 'D'), default='D')
    args = parser.parse_args()
    if not 0 < args.threshold < 1:
        parser.error('Threshold must be finite and inside (0,1)')
    project = args.project_root.resolve()
    output = evaluation_root(project, args.output.resolve())
    output.mkdir(parents=True, exist_ok=False)
    baseline = project / 'docs/release/week8-evidence/benign-calibration/calibration-100.json'
    cases, old = original_cases(baseline)
    os.environ.update(PROMPT_GUARD_MODEL_PATH=str(args.model_path.resolve()),
        PROMPT_GUARD_THRESHOLD=str(args.threshold), PROMPT_GUARD_TIMEOUT_SECONDS='30',
        GUARD_MODEL='qwen2.5:7b',
        HF_HUB_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_PROGRESS_BARS='1',
        OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'config': args.config, 'model': 'qwen2.5:7b',
        'prompt_guard_model': args.model_path.name, 'threshold': args.threshold,
        'baseline_sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
        'synthetic_seed_sha256': hashlib.sha256(args.seed_db.read_bytes()).hexdigest(),
        'baseline_summary': old, 'cases': cases, 'application_source': source_identity(project),
        'configuration': {'timeout_seconds': 30, 'cpu_threads': 4, 'cohort_size': 25, 'guard_model': 'qwen2.5:7b'},
        'method': 'Same 100 prompts, expected tools and synthetic seed; four disposable 25-task cohorts; real Ollama calls.',
        'approval_or_confirmation_calls': False, 'cohorts': [], 'rows': []}
    target = output / 'results.json'
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for offset in range(0, 100, 25):
        directory = output / ('cohort-' + str(offset))
        with servers(project, output, directory, 'ollama', 'qwen2.5:7b', args.ollama_url, sys.executable,
                     seed_db=args.seed_db.resolve()) as (url, db):
            before = snapshot(db)
            with httpx.Client(base_url=url, timeout=180, trust_env=False) as client:
                who = select_config(client, db, args.config)
                for index, case in enumerate(cases[offset:offset + 25]):
                    # Access JWTs expire after five minutes. Refresh authentication
                    # on a fixed cadence; do not rerun failed task attempts.
                    if index and index % 10 == 0:
                        who = select_config(client, db, args.config)
                    row = collect(client, who, db, case, args.config)
                    report['rows'].append(row)
                    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
                    print(f"{len(report['rows'])}/100 {row['id']} {row['status']} utility={row['utility']} pg_false_block={row['prompt_guard_false_block']}", flush=True)
            unchanged = snapshot(db) == before
            if not unchanged:
                raise RuntimeError('Unexpected financial state change in disposable benign run')
        raw = directory / 'raw-model.jsonl'
        calls = [json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
        report['cohorts'].append({'offset': offset, 'financial_state_unchanged': unchanged,
            'actual_primary_calls': sum(bool(call.get('primary')) for call in calls),
            'raw_model_sha256': hashlib.sha256(raw.read_bytes()).hexdigest()})
        if source_identity(project) != report['application_source']:
            raise RuntimeError('Application source changed during utility measurement')
        target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    rows = report['rows']
    report['summary'] = {'planned': 100, 'observed': len(rows), 'utility_successes': sum(r['utility'] for r in rows),
        'prompt_guard_false_blocked_tasks': sum(r['prompt_guard_false_block'] for r in rows),
        'prompt_guard_screened_tasks': sum(any(s.get('stage') == 'prompt_guard_2' for s in r['signals']) for r in rows),
        'status_counts': dict(Counter(r['status'] for r in rows)),
        'primary_calls': sum(c['actual_primary_calls'] for c in report['cohorts']),
        'financial_state_unchanged': all(c['financial_state_unchanged'] for c in report['cohorts'])}
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], indent=2), flush=True)
    return 0 if len(rows) == 100 and all(r['status'] == 'measured' for r in rows) else 2


if __name__ == '__main__':
    raise SystemExit(main())
