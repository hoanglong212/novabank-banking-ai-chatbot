"""Dependency-free executed-line coverage using Python's standard trace module.

This is line coverage, not branch coverage. Runs actual configured pytest tests.
"""
import json
from pathlib import Path
import sys
import trace
import threading
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
FILES = ['posting.py', 'transfers.py', 'ledger.py', 'products.py', 'settlement.py']


def main():
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.base_prefix, str(ROOT / 'backend' / '.venv')])
    previous = threading.gettrace()
    threading.settrace(tracer.globaltrace)
    try:
        code = tracer.runfunc(pytest.main, ['-q', str(ROOT / 'backend' / 'tests'), '--tb=short'])
    finally:
        threading.settrace(previous)
    counts = tracer.results().counts
    report = {'method': 'Python stdlib trace, executed source lines; not branch coverage', 'pytest_exit_code': code, 'modules': []}
    for name in FILES:
        source = ROOT / 'backend' / 'app' / name
        executable = {line for line in trace._find_executable_linenos(str(source)) if isinstance(line, int) and line > 0}
        executed = {line for (filename, line), count in counts.items() if Path(filename).resolve() == source.resolve() and count}
        covered = executable & executed
        report['modules'].append({'file': str(source.relative_to(ROOT)), 'executable_lines': len(executable), 'covered_lines': len(covered),
                                  'coverage_percent': round(len(covered) * 100 / len(executable), 2), 'missing_lines': sorted(executable - covered)})
    total = sum(r['executable_lines'] for r in report['modules']); hit = sum(r['covered_lines'] for r in report['modules'])
    report['financial_line_coverage_percent'] = round(hit * 100 / total, 2)
    output = ROOT / '.local' / 'full-roadmap' / 'financial-coverage.json'; output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if code == 0 and hit / total >= .8 else 1


if __name__ == '__main__':
    raise SystemExit(main())
