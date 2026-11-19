"""Run the repository's published benign calibration cases through a disposable bank."""
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.promptguard_utility import collect, original_cases, select_config
from research.week8_runtime import snapshot


def counts(db, table, column):
    with closing(sqlite3.connect(db)) as connection:
        return dict(connection.execute(f"SELECT {column}, COUNT(*) FROM {table} GROUP BY {column}"))


def verify_published(client, db, project, revision, output, offset):
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=project).strip():
        raise RuntimeError('Run the published comparison against a clean source checkout')
    corpus = project / 'docs/release/week8-evidence/benign-calibration/calibration-100.json'
    cases, _ = original_cases(corpus)
    report = dict(source_commit=revision, config='D', model='qwen2.5:7b',
                  corpus_sha256=hashlib.sha256(corpus.read_bytes()).hexdigest(), planned=len(cases), rows=[])
    report['cohorts'] = []
    if offset:
        report = json.loads(output.read_text(encoding='utf-8'))
        if report['source_commit'] != revision or report['observed'] != offset:
            raise RuntimeError('Unexpected cohort or application revision')
    cohort = {'offset': offset}
    report['cohorts'].append(cohort)
    before = snapshot(db)
    cohort['balances_before_vnd'] = before['accounts']
    cohort['approvals_before'] = counts(db, 'tool_approvals', 'status')
    cohort['security_events_before'] = counts(db, 'security_events', 'event')
    renewed_at = None
    for case in cases[offset:offset + 25]:
        if renewed_at is None or time.monotonic() - renewed_at >= 150:
            who = select_config(client, db, 'D')
            renewed_at = time.monotonic()
        try:
            row = collect(client, who, db, case, 'D')
            record = {k: row[k] for k in ('id', 'family', 'expected_tool', 'status', 'utility',
                                           'proposal_count', 'prompt_guard_false_block') if k in row}
        except (ValueError, RuntimeError) as exc:
            record = dict(id=case['id'], family=case['family'], status='error', utility=False,
                          error_type=type(exc).__name__)
        report['rows'].append(record)
        report['observed'] = len(report['rows'])
        report['successes'] = sum(row['utility'] for row in report['rows'])
        report['statuses'] = dict(Counter(row['status'] for row in report['rows']))
        after = snapshot(db)
        cohort['balances_after_vnd'] = after['accounts']
        cohort['financial_state_unchanged'] = before == after
        cohort['approvals_after'] = counts(db, 'tool_approvals', 'status')
        cohort['security_events_after'] = counts(db, 'security_events', 'event')
        target = output.with_suffix('.tmp')
        target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        target.replace(output)
        if not cohort['financial_state_unchanged']:
            raise RuntimeError('Unexpected financial state change during benign evaluation')
        print(f"{report['observed']}/{len(cases)} {case['id']} {record['status']}", flush=True)
    return int(any(not row['utility'] for row in report['rows'][offset:]))
