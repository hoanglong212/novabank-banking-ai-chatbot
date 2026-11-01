"""Release acceptance gate: an unresolved advisory remains a real failure.

Refresh evidence with dependency scanners; never waive/xfail this test just to
make the release suite green. Tests do not install scanners or dependencies.
"""
from tests.acceptance_helpers import ROOT
import json


def test_SEC_10_fresh_dependency_audits_have_no_unresolved_high_or_critical():
    evidence=ROOT/'docs/release/security-ai-evidence'
    python=json.loads((evidence/'SEC-10-python.json').read_text(encoding='utf-8'))
    npm=json.loads((evidence/'SEC-10-npm.json').read_text(encoding='utf-8'))
    problems=[]
    if python['pip_audit']['exit_code']:
        problems.append('pip-audit unavailable; OSV supplementary scan does not satisfy the required scanner')
    for key,advisory in python['advisories'].items():
        severity=advisory.get('database_specific',{}).get('severity','UNKNOWN')
        if severity in ('HIGH','CRITICAL'):
            problems.append(key+': '+severity)
    for key,advisory in npm['vulnerabilities'].items():
        if advisory['severity'] in ('high','critical'):
            problems.append(key+': '+advisory['severity'])
    assert not problems, '; '.join(problems)
