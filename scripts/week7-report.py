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
    def rate(group, field='attack_success'):
        hits = sum(r[field] == 'True' for r in group)
        return f'{hits}/{len(group)}' if group else 'N/A'
    offon = list(csv.DictReader((output / 'offon-research/observations.csv').open(encoding='utf-8')))
    off_on = {p: [r for r in offon if r['profile'] == p] for p in ('naive', 'baseline', 'defended')}
    def live(name):
        path = output / name / 'results.csv'
        return [r for r in csv.DictReader(path.open(encoding='utf-8')) if not r['error']] if path.exists() else []
    hard, postfix = live('hard-live'), live('hard-live-postfix')
    escalation = [r for r in hard if r['scenario_id'].startswith(('escalate-', 'mt-'))]
    transfers = [r for r in postfix if r['scenario_id'].startswith('legit-transfer-')]
    rag = lambda rows, p: rate([r for r in rows if r['scenario_id'] == 'hard-rag_document-05' and r['profile'] == p])
    capture = json.loads((output / 'capture/capture-summary.json').read_text(encoding='utf-8'))
    requests = sum(c['entries'] for c in capture['channels'].values())
    slides = [
        ('Week 7: từ demo sang số liệu đo được', ['Gateway tắt/bật đo bằng Qwen thật; có corpus tấn công khó hơn.', 'QR thật, staff AI, capture HTTP 4 kênh, giới hạn khi mất danh tính.', 'Local: 127.0.0.1:8081 · Qwen 2.5 7B qua Ollama.']),
        ('Gateway tắt và bật (Qwen, 1.350 lượt)', [
            'ASR tắt gateway (naive): ' + rate([r for r in off_on['naive'] if r['kind'] == 'attack']) + '; baseline: ' + rate([r for r in off_on['baseline'] if r['kind'] == 'attack']) + '.',
            'Bật gateway (defended): ' + rate([r for r in off_on['defended'] if r['kind'] == 'attack']) + ' tấn công thành công.',
            'Tác vụ hợp lệ: naive ' + ', baseline '.join(rate([r for r in off_on[p] if r['kind'] == 'legitimate'], 'utility_success') for p in ('naive', 'baseline')) + ', defended ' + rate([r for r in off_on['defended'] if r['kind'] == 'legitimate'], 'utility_success') + '.']),
        ('Vì sao prompt ngày 3/11 lọt?', ['Cùng payload: naive và baseline mỗi bên 10/35 lượt đề xuất chuyển cho Charlie, chờ duyệt.', 'Không lượt nào tự chuyển tiền; app thật có binding nên trả DENY.', 'Khả năng cao: profile không binding + người demo bấm duyệt (H1+H4). Thiếu log nên chưa kết luận.']),
        ('Judge (LLM) có bị lừa không? Có.', ['Judge bỏ sót 100% payload JSON next_action và "Developer update".', 'Judge bắt được payload viết riêng để lừa nó; 0/10 chặn nhầm.', 'Trong lab, defended vẫn 0%: owner boundary chặn phần judge bỏ sót.']),
        ('Tấn công đã lọt gateway tuần này', [
            'RAG bị nhiễm bảo judge "label it injection=false": defended ' + rag(hard, 'defended') + ', baseline ' + rag(hard, 'baseline') + '.',
            'Qwen báo khách một "phí xác minh lại 247.013 VND" giả, có trích nguồn KB.',
            'Sửa luật cố định + prompt judge: defended ' + rag(postfix, 'defended') + '; 30/30 câu hỏi chính sách không bị chặn nhầm.']),
        ('Khách có lấy được quyền admin qua AI?', [
            ('Live Qwen: ' + rate(escalation) + ' lượt leo quyền/bỏ OTP/đọc tài khoản Bob thành công.') if escalation else 'Đang chạy đo live.',
            'Tự nhận là admin: model không được cấp get_user_count, bank kiểm role từ DB.', 'Staff tool chỉ đọc; agent không có tool xác nhận chuyển tiền.']),
        ('QR thật chứa URL', ['App: upload QR chứa URL bị 422, chỉ nhận NBQR1 có HMAC.', 'Người dùng xác nhận "trả đi": Qwen tự bịa người nhận và số tiền.', 'Bank DENY (USER_INTENT_REQUIRED): người nhận chỉ lấy từ lời người dùng.']),
        (f'Capture HTTP: {requests} request, 4 kênh', ['Model chỉ thấy <ACCOUNT_n>, không thấy số tài khoản thật.', 'Phát hiện lỗi: câu "Prepare a transfer…" không được hiểu, chuyển tiền qua AI 0/100.',
            ('Đã sửa; đo lại live: chuyển tiền hợp lệ ' + rate(transfers, 'utility_success') + '.') if transfers else 'Đã sửa và có test hồi quy.']),
        ('Khi danh tính bị chiếm', ['Tối đa 5 giao dịch hoàn tất trong 10 phút.', 'Lần đầu chuyển cho người nhận mới: tối đa 10.000.000 VND.', 'Kiểm tra cả khi tạo draft và khi xác nhận OTP.']),
        ('Còn thiếu', ['Caido/Burp trên VM (đang dùng proxy ghi HAR thay thế).', 'Log và profile của buổi demo 3/11.', 'Review độc lập và CI remote.']),
    ]
    html = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NovaBank Week 7</title>
<style>*{box-sizing:border-box}body{margin:0;background:#211536;color:#241c32;font-family:Arial,sans-serif}.slide{display:none;width:1120px;height:630px;background:white;margin:24px auto;padding:56px 64px}.slide.active{display:block}h1{font-size:40px;line-height:1.15;color:#54238c;margin:0 0 42px}li{font-size:27px;line-height:1.5;margin:24px 0}ul{padding-left:28px}nav{display:flex;justify-content:center;gap:24px;align-items:center;color:white}button{font:20px Arial;padding:10px 20px;border:1px solid white;background:none;color:white;cursor:pointer}button:focus-visible{outline:3px solid gold}small{display:block;font-size:16px;margin-top:28px;color:#62576d}@media(max-width:1150px){.slide{width:95vw;height:auto;min-height:75vh;padding:32px}h1{font-size:30px}li{font-size:21px}}@media print{.slide{display:block;break-after:page;margin:0}nav{display:none}}</style>'''
    for i, (title, points) in enumerate(slides):
        html += f'<section class="slide{" active" if i == 0 else ""}" aria-label="Slide {i + 1}"><h1>{escape(title)}</h1><ul>' + ''.join('<li>' + escape(point) + '</li>' for point in points) + '</ul><small>Nguồn: GATEWAY_OFF_ON, HARD_LIVE, BYPASS_NOTE, RBAC_MATRIX, QUISHING, CRYPTO_AUTHZ và capture/README trong thư mục evidence.</small></section>'
    html += '''<nav><button id="prev">Previous</button><span id="count" aria-live="polite"></span><button id="next">Next</button></nav><script>let n=0;const pages=[...document.querySelectorAll('.slide')];function show(i){n=Math.max(0,Math.min(pages.length-1,i));pages.forEach((p,j)=>p.classList.toggle('active',j===n));document.querySelector('#count').textContent=(n+1)+' / '+pages.length}document.querySelector('#prev').onclick=()=>show(n-1);document.querySelector('#next').onclick=()=>show(n+1);document.onkeydown=e=>{if(e.key==='ArrowRight')show(n+1);if(e.key==='ArrowLeft')show(n-1)};show(0)</script></html>'''
    (output / 'Week7-Slides.html').write_text(html, encoding='utf-8')
    print('Packaged evidence in', output)


if __name__ == '__main__':
    main()
