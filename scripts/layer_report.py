"""Run the layer verification tests and print one table per defense layer.

Usage (from anywhere):
  <repo>/backend/.venv/Scripts/python.exe layer_report.py "<repo>"
Writes layer_report.md next to this script as well.
"""
from collections import defaultdict
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LAYERS = [
    ('L0a', '0a · Input guard (luồng 1)'), ('L0b', '0b · Intent binding (luồng 1)'),
    ('L1a', '1a · Provenance (luồng 2)'), ('L1b', '1b · Bộ phát hiện (luồng 2)'), ('L1c', '1c · Cách ly nguồn'),
    ('L2', '2 · Spotlighting'), ('LP', 'P · Ẩn danh hoá'), ('L3', '3 · Action Gateway'),
    ('L4', '4 · Duyệt + xác nhận + token'), ('L5', '5 · Lọc đầu ra'), ('L6', '6 · security_events'),
    ('LT', 'T · Dual LLM cho ticket'),
]

root = Path(sys.argv[1]).resolve()
backend = root / 'backend'
test_file = backend / 'tests' / 'test_layer_verification.py'
if not test_file.is_file():
    sys.exit('Copy test_layer_verification.py into ' + str(test_file.parent) + ' first.')

commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=root, capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'backend/app', 'agent_service'], cwd=root,
                       capture_output=True, text=True).stdout.strip()
xml_path = Path(tempfile.gettempdir()) / 'novabank_layer_report.xml'
env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(root), str(backend)])}
proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-rxX', 'tests/test_layer_verification.py',
                       '--junitxml', str(xml_path)], cwd=backend, env=env, capture_output=True, text=True,
                      encoding='utf-8', errors='replace')

counts = defaultdict(lambda: defaultdict(int))
failures = defaultdict(list)
for case in ET.parse(xml_path).getroot().iter('testcase'):
    name = case.get('name')
    layer = next((key for key, _ in sorted(LAYERS, key=lambda kv: -len(kv[0])) if name.startswith('test_' + key + '_')), '?')
    skipped = case.find('skipped')
    if case.find('failure') is not None or case.find('error') is not None:
        counts[layer]['fail'] += 1
        failures[layer].append(name)
    elif skipped is not None and 'xfail' in (skipped.get('type', '') + skipped.get('message', '')).lower():
        counts[layer]['gap'] += 1
    elif skipped is not None:
        counts[layer]['skip'] += 1
    else:
        counts[layer]['pass'] += 1

lines = [f'# Kiểm tra từng tầng — commit {commit}' + (' (backend/app hoặc agent_service có thay đổi chưa commit!)' if dirty else ''), '',
         '| Tầng | Đạt | Không đạt | Lỗ hổng đã biết | Kết luận |', '|---|---|---|---|---|']
all_ok = True
for key, label in LAYERS:
    c = counts[key]
    verdict = 'HOẠT ĐỘNG ĐÚNG' if c['fail'] == 0 and c['pass'] else ('KHÔNG ĐẠT' if c['fail'] else 'KHÔNG CÓ TEST')
    if c['gap'] and c['fail'] == 0:
        verdict += ' (có lỗ hổng đã biết)'
    all_ok &= c['fail'] == 0
    lines.append(f"| {label} | {c['pass']} | {c['fail']} | {c['gap']} | {verdict} |")
for key, names in failures.items():
    lines += ['', f'**Không đạt ở {key}:**'] + ['- ' + n for n in names]
lines += ['', 'TẤT CẢ CÁC TẦNG ĐẠT' if all_ok else 'CÓ TẦNG KHÔNG ĐẠT — xem chi tiết pytest bên dưới']
report = '\n'.join(lines)
print(report)
(Path(__file__).resolve().parent / 'layer_report.md').write_text(report + '\n', encoding='utf-8')
if not all_ok:
    print('\n' + '\n'.join(proc.stdout.splitlines()[-40:]))
sys.exit(0 if all_ok else 1)
