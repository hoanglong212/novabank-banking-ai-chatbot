"""Export observed API authorization cases; N/A remains explicit, never a fabricated pass."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run-id', default='latest')
    args = parser.parse_args()
    matrix = json.loads((args.project_root / 'backend/tests/route_matrix.json').read_text(encoding='utf-8'))
    rows = [json.loads(line) for line in args.evidence.read_text(encoding='utf-8').splitlines() if line.strip()]
    run = rows[-1]['run'] if args.run_id == 'latest' else args.run_id
    rows = [row for row in rows if row['run'] == run]
    if not rows:
        raise ValueError('No observed cases for requested run')
    digest = hashlib.sha256(json.dumps(matrix, sort_keys=True).encode()).hexdigest()
    drift = {row.get('matrix_digest') for row in rows} != {digest}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'api-observations.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    counts = Counter(row['status'] for row in rows)
    summary = {'run': run, 'runtime_sources': sorted({r['runtime_source'] for r in rows}),
        'route_count': len(matrix), 'observations': len(rows), 'status_counts': dict(counts), 'route_matrix_drift': drift,
        'unobserved_routes': [entry for entry in matrix if not any(r['method'] == entry['method'] and r['path'] == entry['path'] for r in rows)],
        'credentials_included': False, 'caido_capture': 'not_available; TestClient HTTP evidence only'}
    (args.out / 'api-summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    def result_for(entries, prefix):
        selected = [r for r in entries if r['case'].startswith(prefix)]
        if any(r['status'] == 'failed' for r in selected): return 'FAIL'
        passed = [r for r in selected if r['status'] == 'passed']
        if passed: return 'PASS ' + ','.join(sorted({str(r.get('actual', 'invariant')) for r in passed}))
        if selected: return 'N/A: ' + selected[0].get('reason', '')
        return 'NOT RUN'
    lines = ['# API authorization test evidence', '',
        f'Run `{run}`. Matrix routes: {len(matrix)}. Observations: {len(rows)}. Statuses: {dict(counts)}. Matrix drift: {drift}.', '',
        'All resources are from disposable TestClient databases. Tests use real authentication, TOTP setup, new-payee step-up and email OTP to create the owned receipt. '
        'No live/demo database was changed. Resource-negative cases target existing Alice-owned records using Bob credentials; they are not missing-ID or invalid-DTO stand-ins.', '',
        '| Method | Route | Scope | Anonymous | Cross-owner selector | Forbidden roles | Type/bounds |',
        '|---|---|---|---|---|---|---|']
    for entry in matrix:
        selected = [r for r in rows if r['method'] == entry['method'] and r['path'] == entry['path']]
        owner = [r for r in selected if r['case'].startswith(('cross_owner', 'implicit_owner'))]
        owner_result = 'PASS ' + ','.join(sorted({str(r.get('actual', 'invariant')) for r in owner if r['status'] == 'passed'})) if any(r['status'] == 'passed' for r in owner) else result_for(selected, 'cross_owner')
        if any(r['status'] == 'failed' for r in owner): owner_result = 'FAIL'
        lines.append(f'| {entry["method"]} | `{entry["path"]}` | {entry.get("scope")} | {result_for(selected,"anonymous")} | {owner_result} | {result_for(selected,"forbidden_role")} | {result_for(selected,"invalid_type_or_length")} |')
    lines += ['', '## Additional verified controls', '',
        '- Ordinary bank JWTs cannot call delegated-only endpoints. A Bob delegation cannot select an Alice run via a query or read her balance through tool arguments; Bob own-balance positive control remains allowed.',
        '- A completed transfer replay with the same key returns the original receipt, a different key is rejected, and balances do not change again.',
        '- Otherwise-valid oversized account/ticket/message/run/preview bodies and a string instead of integer transfer amount are rejected with 422.',
        '- Owner positive controls return 200 for real ticket, attachment, transfer, transaction, receipt, run, approval, conversation and outbox resources.', '',
        '## Applicability and limits', '',
        '- Public/static/login-challenge surfaces are not bearer-protected; public does not mean OTP/refresh tokens are unnecessary for credential-specific actions.',
        '- Global staff/research resources have role boundaries rather than a customer owner. Shared approved knowledge also has no per-customer owner. These are explicit N/A for IDOR, not passing wrong-owner tests.',
        '- Identity-derived routes without a resource selector have no cross-owner pointer. Read collections are additionally tested against injected owner_id/user_id query selectors. Write DTOs remain strict and are covered by type/mass-assignment tests.',
        '- Replay is verified for money confirmation here; broader auth/MFA/action replay semantics are covered by existing session/MFA/product suites, not claimed as per-route replay coverage by this table.',
        '- JSON field-type probes cover typed bodies; endpoints with no JSON DTO are N/A for that probe. The table does not claim every possible parameter/value or concurrency interleaving was explored.',
        '- Caido was not used or installed. The accompanying redacted HTTP examples are TestClient equivalents, not screenshots of a proxy application.',
        '- The normal full backend suite, independent review and browser acceptance remain separate gates. No security guarantee follows from green tests.']
    (args.out / 'API_TESTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    examples = []
    for row in [r for r in rows if r['status'] == 'passed' and r['case'] in ('cross_owner', 'ordinary_token_on_delegated_route', 'anonymous')][:3]:
        examples += [f'### {row["case"]}: observed HTTP {row.get("actual")}',
            f'{row["method"]} {row.get("concrete_path") or row["path"]} HTTP/1.1',
            'Host: testserver', 'Authorization: Bearer [REDACTED OR ABSENT]',
            '# Payload values omitted; complete fixture and valid DTO are in test_week8_api_matrix.py.', '']
    (args.out / 'api-http-examples.http').write_text('\n'.join(examples), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 1 if counts['failed'] or drift or summary['unobserved_routes'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
