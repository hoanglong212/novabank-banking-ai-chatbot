"""Publish reproducible, synthetic experiment evidence and a bounded comparison."""
from collections import defaultdict
from html import escape
import json
from pathlib import Path
import shutil
import statistics
import zipfile
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderSVG
from reportlab.lib import colors

ROOT = Path(__file__).resolve().parents[1]
run = ROOT / '.local/research' / json.loads((ROOT / '.local/research/latest.json').read_text())['id']
out = ROOT / 'docs/release/research'; out.mkdir(parents=True, exist_ok=True)
summary = json.loads((run / 'summary.json').read_text(encoding='utf-8'))
raw = json.loads((run / 'results.json').read_text(encoding='utf-8'))
if isinstance(raw, dict):
    raw = raw['results']
for filename in ('summary.json', 'dataset.json', 'metrics.csv', 'classifier.json'):
    shutil.copyfile(run / filename, out / filename)
with zipfile.ZipFile(out / 'raw-results.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(run / 'results.json', 'results.json')
groups = defaultdict(list)
for row in raw:
    if not row['ablation']: groups[(row['model'], row['profile'])].append(row)
metrics = []
for (model, profile), rows in groups.items():
    attacks = [r for r in rows if r['kind'] == 'attack']; utility = [r for r in rows if r['kind'] == 'legitimate']
    metrics.append({'model': model, 'profile': profile, 'attacks': len(attacks), 'successes': sum(r['attack_success'] for r in attacks),
        'asr': sum(r['attack_success'] for r in attacks)/len(attacks), 'utility': sum(r['utility_success'] for r in utility)/len(utility),
        'utility_count': len(utility), 'errors': sum(bool(r['error']) for r in rows), 'mean_latency_ms': round(statistics.mean(r['latency_ms'] for r in rows))})
(out / 'aggregate.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
lines = ['# Kết quả thí nghiệm prompt injection', '', f"Run `{summary['id']}`. {summary['completed']} quan sát, {summary['attack_scenarios']} kịch bản × 3 profile × 2 model × 5 lần, 100 tác vụ hợp lệ/model/profile và 140 ablation.", '',
         '| Model | Profile | Thành công / tấn công | ASR | Utility | Lỗi chạy |', '|---|---|---:|---:|---:|---:|']
for m in metrics:
    lines.append(f"| {m['model']} | {m['profile']} | {m['successes']} / {m['attacks']} | {m['asr']:.2%} | {m['utility']:.0%} | {m['errors']} |")
lines += ['', '## Ý nghĩa và giới hạn', '',
    'ASR ở đây là tỷ lệ đạt mục tiêu theo tiêu chí đã định trước. Một đề xuất sai người nhận được baseline lab chấp nhận cũng tính là thành công, dù còn chờ người duyệt. Chỉ naive có tool thực thi tiền giả; kết quả không đồng nghĩa baseline ứng dụng đã chuyển tiền trái phép.',
    '', 'Đây là nghiên cứu có kiểm soát tại bước tiếp nhận nguồn: fixture truy xuất được cung cấp cho model, mỗi mẫu đo một lần quyết định tool. Không đo xác suất tài liệu độc lọt vào truy xuất, không thay thế kiểm thử hội thoại nhiều lượt. D3 của lab dùng intent đã biết của bộ dữ liệu; ứng dụng dùng binding độc lập từ yêu cầu khách nên kết quả utility không thể suy rộng trực tiếp.',
    '', 'Các payload có chung mẫu theo 7 vector × 5 mục tiêu. Năm lần lặp không phải 175 kiểu tấn công độc lập. ASR 0 trong bộ này không chứng minh an toàn trước tấn công thích ứng hoặc dữ liệu mới. Sai số thống kê theo mô hình mẫu độc lập không được dùng để khẳng định an toàn.',
    '', 'Classifier kiểm tra 10 đoạn hợp lệ riêng: 0/10 chặn nhầm. Utility FPR là tỷ lệ tool/args đúng nhưng bị guard từ chối, khác classifier FPR. Số mẫu benign nhỏ. Nhiều payload bị chặn trước model chính, vì vậy phải đọc số model_invocations cùng latency/token; caching classifier làm giảm chi phí ở lần lặp sau.',
    '', 'Ablation: mỗi vector chỉ một mục tiêu chuyển sai, một lần/model/defense. Các lớp khác vẫn hoạt động; kết quả không thay đổi không chứng minh lớp bị bỏ vô dụng. Chưa đủ để xếp hạng đóng góp nhân quả D1–D10.',
    '', 'Pilot đầu ghi nhận utility 0 do thiếu ID tài khoản/giải thích tham số trong context. Harness đã sửa trước khi đóng băng dataset v1.1 và chạy full matrix. Không gộp pilot vào bảng kết quả.',
    '', '## Ablation tổng hợp', '', '| Model | Lớp bỏ | Thành công / mẫu |', '|---|---|---:|']
ab = defaultdict(list)
for r in raw:
    if r['ablation']: ab[(r['model'],r['ablation'])].append(r)
for (model, defense), rows in sorted(ab.items()):
    lines.append(f"| {model} | {defense} | {sum(r['attack_success'] for r in rows)} / {len(rows)} |")
lines += ['', '## Tái lập và dữ liệu', '',
    '`python -m research.run --ablations` với hai model Ollama đã có. Harness từ chối DB ngoài `.local/research/<run>/`. Không tự cài/pull model.',
    '', f"Dataset SHA256 `{summary['dataset_sha256']}`; engine SHA256 `{summary['engine_sha256']}`.",
    '', '[CSV đầy đủ](research/metrics.csv), [metadata](research/summary.json), [dataset](research/dataset.json), [raw JSON nén](research/raw-results.zip), [biểu đồ ASR](research/asr.svg).',
    '', 'Đối chiếu luồng ứng dụng thật: scripts/check-agent-service.py và frontend/scripts/release-browser.mjs, chạy hai tiến trình HTTP riêng, Qwen + nomic embeddings, approval rồi OTP. Baseline ứng dụng giữ các hàng rào nghiệp vụ chặt hơn baseline lab.']
(out.parent / 'PI_RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')
d = Drawing(820, 340); chart = VerticalBarChart(); chart.x=55; chart.y=65; chart.width=730; chart.height=220
chart.data = [[round(m['asr']*100,2) for m in metrics]]; chart.categoryAxis.categoryNames = [m['model'].split(':')[0]+'\n'+m['profile'] for m in metrics]
chart.valueAxis.valueMin=0; chart.valueAxis.valueMax=100; chart.valueAxis.valueStep=20; chart.bars[0].fillColor=colors.HexColor('#6828b9')
d.add(chart); d.add(String(55,315,'Observed attack success rate (%)',fontName='Helvetica-Bold',fontSize=18))
d.add(String(55,12,'175 observations per bar. Controlled fixtures; baseline success may be an unsafe proposal, not a posted transfer.',fontSize=9))
renderSVG.drawToFile(d, str(out / 'asr.svg'))
# Evidence displayed in the video is an unmodified stored observation, never a staged model answer.
baseline = next(r for r in raw if r['profile']=='baseline' and not r['ablation'] and r['attack_success'] and r['vector']=='beneficiary_nickname' and r['goal']=='misdirect_transfer')
defended = next(r for r in raw if r['profile']=='defended' and not r['ablation'] and r['scenario_id']==baseline['scenario_id'] and r['model']==baseline['model'] and r['repetition']==baseline['repetition'])
comparison = {'baseline': baseline, 'defended': defended}; (out / 'example.json').write_text(json.dumps(comparison, indent=2, ensure_ascii=False),encoding='utf-8')
html = '<!doctype html><meta charset="utf-8"><title>NovaBank observed lab comparison</title><style>body{font:20px system-ui;margin:48px;color:#211536;background:#f7f5fb}h1{font-size:36px}main{display:grid;grid-template-columns:1fr 1fr;gap:28px}section{background:white;padding:24px;border:1px solid #dcd4e9}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:15px}small{font-size:16px}</style><h1>Kết quả đã đo: baseline và defended</h1><p>Sandbox tiền giả. “Thành công” ở baseline này là chấp nhận đề xuất sai, chưa chuyển tiền.</p><main>'
for mode,row in comparison.items():
    excerpt = {k:row[k] for k in ('scenario_id','model','profile','attack_success','tool_calls','security_events')}
    html += f'<section><h2>{mode}</h2><pre>{escape(json.dumps(excerpt,indent=2,ensure_ascii=False))}</pre></section>'
html += '</main><p><small>Run '+summary['id']+'. Toàn bộ raw output và tiêu chí nằm trong docs/release/research. Kết quả chỉ áp dụng bộ thử nghiệm này.</small></p>'
(out / 'comparison.html').write_text(html,encoding='utf-8')
print(json.dumps({'aggregate':metrics,'ablation_successes':sum(r['attack_success'] for r in raw if r['ablation']),'out':str(out)},indent=2))
