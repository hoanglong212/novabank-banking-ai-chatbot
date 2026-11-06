"""Package measured Week 7 evidence; preserve unmeasured items as pending."""
from collections import Counter
import argparse
import csv
from html import escape
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/release/week7-evidence'


def fraction(rows, field, *, require_safe=False):
    hits = sum(r[field] == 'True' and (not require_safe or r['attack_success'] != 'True') for r in rows)
    return f'{hits}/{len(rows)} ({hits / len(rows):.1%})' if rows else 'N/A'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'tools/live_attack/out')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    output = args.out
    output.mkdir(parents=True, exist_ok=True)
    source = args.source
    summary = json.loads((source / 'summary.json').read_text(encoding='utf-8'))
    rows = list(csv.DictReader((source / 'results.csv').open(encoding='utf-8')))
    profiles = ['legacy-off', 'baseline', 'defended']
    table = ['| Metric | legacy-off | baseline | defended |', '|---|---:|---:|---:|']
    buckets = [[r for r in rows if r['profile'] == p and not r['error']] for p in profiles]
    table.append('| Targeted ASR (observed attacker goal) | ' + ' | '.join(fraction([r for r in group if r['kind'] == 'attack'], 'attack_success') for group in buckets) + ' |')
    applicable = [[r for r in rows if r['profile'] == p and not r['error'].startswith('NOT_APPLICABLE')] for p in profiles]
    table.append('| Benign tool utility (including execution failures) | ' + ' | '.join(fraction([r for r in group if r['kind'] == 'legitimate'], 'utility_success') for group in applicable) + ' |')
    table.append('| Benign tool utility (completed trials only) | ' + ' | '.join(fraction([r for r in group if r['kind'] == 'legitimate'], 'utility_success') for group in buckets) + ' |')
    table.append('| Tool utility under attack | ' + ' | '.join(fraction([r for r in group if r['kind'] == 'attack'], 'utility_success', require_safe=True) for group in buckets) + ' |')
    table.append('| Excluded / not applicable | ' + ' | '.join(str(sum(r['profile'] == p and r['error'].startswith('NOT_APPLICABLE') for r in rows)) for p in profiles) + ' |')
    table.append('| Execution errors | ' + ' | '.join(str(sum(r['profile'] == p and bool(r['error']) and not r['error'].startswith('NOT_APPLICABLE') for r in rows)) for p in profiles) + ' |')
    llm = summary['provider'] == 'ollama'
    label = 'Ollama' if llm else 'mock only'
    scenarios = len({r['scenario_id'] for r in rows})
    counts = Counter(r['profile'] for r in rows)
    execution_errors = sum(bool(r['error']) and not r['error'].startswith('NOT_APPLICABLE') for r in rows)
    exclusions = sum(r['error'].startswith('NOT_APPLICABLE') for r in rows)
    text = '# Live HTTP results — ' + label + '\n\n'
    text += ('**Real local model configured; some requests are rejected before model invocation.**\n\n' if llm else
             '**No LLM was invoked. These numbers are not evidence of LLM robustness.**\n\n')
    text += f"{len(rows)} scheduled observations; {scenarios} scenarios × {len(counts)} paths × {summary['repetitions']} repetitions. Subset: {summary['subset']}.\n\n" + '\n'.join(table)
    text += '\n\nBaseline and legacy retain controls; neither is true gateway-off. No confirmation endpoint was called. Utility is a tool/argument completion proxy, not AgentDojo semantic task grading. Missing canary goals and staff legacy are excluded. Except for the explicitly labelled benign-utility row that includes execution failures, rate denominators exclude errors and are conditional on completed trials, not overall reliability. Read the error counts alongside them. See KNOWN_FAILURES.md for defects found during the run and separate post-fix checks.\n\n## Per-scenario ASR\n\n| Scenario | legacy-off | baseline | defended |\n|---|---:|---:|---:|\n'
    for scenario in dict.fromkeys(r['scenario_id'] for r in rows if r['kind'] == 'attack'):
        text += '| ' + scenario + ' | ' + ' | '.join(fraction([r for r in group if r['scenario_id'] == scenario], 'attack_success') for group in buckets) + ' |\n'
    text += '\n## Source observations (attack trials only)\n\nA source tool call does not prove that all injected text reached the model. Direct input can also be blocked before model invocation. In mock mode there is no model consumption. Both app paths use temperature 0, so repetitions are repeated observations rather than samples at nonzero temperature.\n\n'
    text += '\n'.join(f'- {profile} / {vector} / {exposure}: {count}' for (profile, vector, exposure), count in sorted(Counter((r['profile'], r['vector'], r['source_exposure']) for r in rows if not r['error'] and r['kind'] == 'attack').items()))
    (output / 'asr-table.md').write_text(text + '\n', encoding='utf-8')
    for name in ('results.csv', 'summary.json'):
        shutil.copy2(source / name, output / name)
    for name in ('BYPASS_NOTE.md', 'RBAC_MATRIX.md', 'CRYPTO_AUTHZ.md'):
        shutil.copy2(ROOT / 'docs/release' / name, output / name)
    shutil.copy2(ROOT / 'docs/research/QUISHING.md', output / 'QUISHING.md')
    postfix_note = 'Xem completion.md để phân biệt triển khai local và toàn bộ nghiên cứu.'
    comparison_file = output / 'postfix-regression/comparison.json'
    if comparison_file.exists():
        comparison = json.loads(comparison_file.read_text(encoding='utf-8'))
        before, after = comparison['before'], comparison['after']
        postfix_note = f"{after['trials']} lượt chạy lại: lỗi {before['execution_errors']} → {after['execution_errors']}; upstream error còn {after['termination_reasons'].get('UPSTREAM_ERROR', 0)}."
    slides = [
        ('Week 7: ứng dụng đã chạy local', ['Outbox OTP, staff assistant chỉ đọc và chuyển tiền qua URL.', 'Baseline: 359 pytest, 17 nhóm component, 16 E2E.', 'Local: 127.0.0.1:8081 · Qwen 2.5 7B qua Ollama.']),
        ('Prompt demo: biết gì, chưa biết gì?', ['SYSTEM OVERRIDE đã lọt regex trước thay đổi.', 'Bản mới chặn trước khi tạo run; binding Bob → Charlie bị DENY.', 'Chưa có profile hoặc log ngày 3/11 để kết luận nguyên nhân lịch sử.']),
        ('Role quyết định quyền, không phải prompt', ['Customer không gọi staff tools.', 'Support đọc ticket; operations và auditor đọc giao dịch đã che dữ liệu.', 'Admin đếm user và đọc báo cáo; không có công cụ AI chuyển tiền.']),
        ('OTP chỉ nằm trong hộp thư demo', ['Transfer API không trả demo_otp.', 'Review → verification → receipt: mỗi bước tải trạng thái từ server.', 'Outbox chỉ bật ENV=demo; không coi nó là email độc lập trong production.']),
        (f'{len(rows):,} lượt HTTP · {label}', [f"{scenarios} scenario; {summary['repetitions']} lần mỗi path.",
            'ASR: ' + '; '.join(p + ' ' + fraction([r for r in group if r['kind'] == 'attack'], 'attack_success') for p, group in zip(profiles, buckets)),
            f'{execution_errors} lượt lỗi; {exclusions} lượt không áp dụng. Xem asr-table và KNOWN_FAILURES.']),
        ('QR: thử nới quyền trong lab riêng', ['App: NBQR1 có HMAC, schema không URL, không tool fetch.', 'Qwen experimental đã fetch trang lab nhưng không gọi prepare_transfer.', 'Probe scripted riêng bị bank DENY; một lượt model không chứng minh an toàn.']),
        ('Sau sửa và phần chưa nghiệm thu', [postfix_note, 'Còn thiếu Caido/VM capture và profile/log demo ngày 3/11.', 'Ruff và ESLint đã đạt; còn review độc lập và CI remote.']),
    ]
    html = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NovaBank Week 7</title>
<style>*{box-sizing:border-box}body{margin:0;background:#211536;color:#241c32;font-family:Arial,sans-serif}.slide{display:none;width:1120px;height:630px;background:white;margin:24px auto;padding:56px 64px}.slide.active{display:block}h1{font-size:40px;line-height:1.15;color:#54238c;margin:0 0 42px}li{font-size:27px;line-height:1.5;margin:24px 0}ul{padding-left:28px}nav{display:flex;justify-content:center;gap:24px;align-items:center;color:white}button{font:20px Arial;padding:10px 20px;border:1px solid white;background:none;color:white;cursor:pointer}button:focus-visible{outline:3px solid gold}small{display:block;font-size:16px;margin-top:28px;color:#62576d}@media(max-width:1150px){.slide{width:95vw;height:auto;min-height:75vh;padding:32px}h1{font-size:30px}li{font-size:21px}}@media print{.slide{display:block;break-after:page;margin:0}nav{display:none}}</style>'''
    for i, (title, points) in enumerate(slides):
        html += f'<section class="slide{" active" if i == 0 else ""}" aria-label="Slide {i + 1}"><h1>{escape(title)}</h1><ul>' + ''.join('<li>' + escape(point) + '</li>' for point in points) + '</ul><small>Nguồn: BYPASS_NOTE, RBAC_MATRIX, asr-table, QUISHING và completion trong thư mục evidence.</small></section>'
    html += '''<nav><button id="prev">Previous</button><span id="count" aria-live="polite"></span><button id="next">Next</button></nav><script>let n=0;const pages=[...document.querySelectorAll('.slide')];function show(i){n=Math.max(0,Math.min(pages.length-1,i));pages.forEach((p,j)=>p.classList.toggle('active',j===n));document.querySelector('#count').textContent=(n+1)+' / '+pages.length}document.querySelector('#prev').onclick=()=>show(n-1);document.querySelector('#next').onclick=()=>show(n+1);document.onkeydown=e=>{if(e.key==='ArrowRight')show(n+1);if(e.key==='ArrowLeft')show(n-1)};show(0)</script></html>'''
    (output / 'Week7-Slides.html').write_text(html, encoding='utf-8')
    print('Packaged evidence in', output)


if __name__ == '__main__':
    main()
