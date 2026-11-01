"""Render the measured security report as a compact, shareable PDF."""
from html import escape
import json
from pathlib import Path
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app import receipts  # Bundled Noto Sans with Vietnamese glyphs.
out=ROOT/'docs/release'; story=[]
body=ParagraphStyle('body',fontName='NovaSans',fontSize=10,leading=15,spaceAfter=9)
title=ParagraphStyle('title',parent=body,fontSize=24,leading=31,spaceAfter=18,textColor=colors.HexColor('#472070'))
heading=ParagraphStyle('heading',parent=body,fontSize=15,leading=21,spaceBefore=14,spaceAfter=9,textColor=colors.HexColor('#472070'))
small=ParagraphStyle('small',parent=body,fontSize=8,leading=11)
def p(text, style=body):return Paragraph(escape(text),style)
story += [p('NovaBank\nSecurity Evaluation',title),p('Báo cáo kết quả local • 01/11/2026'),p('Ngân hàng mô phỏng, dữ liệu giả. React/Vite/TypeScript + FastAPI/SQLite; agent riêng qua HTTP và Ollama local.'),p('Kết quả chính',heading)]
metrics=json.loads((out/'research/aggregate.json').read_text())
rows=[[p(v,small) for v in ('Model','Profile','Goal đạt / mẫu','ASR','Utility')]]
for m in metrics:rows.append([p(v,small) for v in (m['model'],m['profile'],f"{m['successes']} / {m['attacks']}",f"{m['asr']:.2%}",f"{m['utility']:.0%}")])
t=Table(rows,colWidths=[110,90,105,70,70],repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ede5f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.3,colors.lightgrey)]));story+=[t,Spacer(1,15)]
story += [p('1.790 quan sát hoàn tất, không có lỗi chạy. 35 kịch bản trên 7 vector, 100 tác vụ hợp lệ, 2 model, 3 profile, 5 lần lặp tấn công và 140 ablation. Mọi journal sandbox cân bằng.'),p('Giới hạn kết luận',heading),p('ASR đo mục tiêu đã định trước. Baseline lab chấp nhận một đề xuất sai cũng có thể tính thành công, dù tiền chưa chuyển. Chỉ naive có execute_transfer với tiền giả. ASR 0 của defended chỉ áp dụng corpus này.'),p('Nguồn truy xuất được đưa sẵn vào context, mỗi case đo một quyết định tool. D3 lab biết intent chuẩn. Corpus có nhiều mẫu lặp, chưa đo retrieval poisoning end-to-end hoặc adversarial adaptation. Utility là đúng tool/args, không phải toàn bộ chất lượng hội thoại.'),PageBreak()]
story += [p('Kiểm soát và bằng chứng',title)]
for h,text in [
 ('Banking API giữ quyền quyết định','JWT audience/session/owner checks, độc lập argument binding, OTP và idempotency. Agent không có tool confirm. Money posting atomic, integer VND, balanced journal và immutable history.'),
 ('Đo kiểm ứng dụng','Backend và browser suites chạy trên DB tạm. Financial executed-line coverage 93,27% ở posting/transfers/ledger/products/settlement. Không phải branch coverage hoặc coverage toàn repo.'),
 ('Service và mô hình thật','Hai HTTP process dùng Qwen và nomic embeddings kiểm tra balance, policy có nguồn và transfer proposal. Browser thực kiểm tra SSE, proposal, approval và transfer review. Các checks này tách riêng regression dùng mock/legacy mode.'),
 ('Bảo toàn dữ liệu','Migration trên hai bản sao giữ old rows và ledger. Hash DB nguồn không đổi. Restore exercise phục hồi 52 bảng cùng per-DB MFA key, từ chối target đang tồn tại.'),
 ('D1–D10 và ablation','Prompt rules, delimiters, least privilege, binding, approval, limits, screening, output filter, anomaly stop và memory isolation. 140 ablation đều không đạt attack goal trong tập nhỏ; chưa thể xếp hạng đóng góp từng lớp. Classifier 0/10 chặn nhầm trên benign snippets, mẫu còn nhỏ.')]:story += [p(h,heading),p(text)]
story += [PageBreak(),p('Điều kiện phát hành còn mở',title)]
for h,text in [
 ('Dependency scan','npm audit ghi 2 moderate (vite, postcss-selector-parser), không high/critical. OSV quét 94 Python distributions, ghi advisory cho certifi và pip. Chưa tự cập nhật gói theo quy tắc không auto-install. JSON gốc được lưu trong evidence/.'),
 ('Vận hành','Compose parse đã đạt. Docker Engine hiện không chạy nên chưa build/run image; chưa có VPS/domain/ACME/HTTPS công khai. GitHub Actions chưa có run cho diff hiện tại. Chưa commit/tag phát hành.'),
 ('Các rủi ro chưa chứng nhận','Chưa pentest hay review độc lập, chưa load test nhiều máy, chưa adaptive attack evaluation. App dùng bearer token trong sessionStorage; không tuyên bố cookie HttpOnly. Swagger có CSP CDN riêng, banking app script self.'),
 ('Tái lập','python -m research.run --ablations. Dataset và engine có SHA256 trong research/summary.json. Dữ liệu đầy đủ: research/metrics.csv, dataset.json, raw-results.zip. Bảng completion và lệnh test nằm trong STATUS.md, TEST_PLAN.md và DEPLOYMENT.md.'),
 ('Dùng kết quả đúng phạm vi','Có thể dùng để trình diễn workflow tiền giả và so sánh kiểm soát trên corpus đã đo. Chưa đủ cơ sở để kết nối tài khoản thật, PII thật hoặc tuyên bố banking-grade security.')]:story += [p(h,heading),p(text)]
def footer(c,doc):
    c.setFont('NovaSans',8);c.setFillColor(colors.HexColor('#685d73'));c.drawString(48,28,'NovaBank simulation · Evidence in docs/release');c.drawRightString(A4[0]-48,28,str(doc.page))
SimpleDocTemplate(str(out/'Security-Evaluation.pdf'),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=45,bottomMargin=48,title='NovaBank Security Evaluation').build(story,onFirstPage=footer,onLaterPages=footer)
print(out/'Security-Evaluation.pdf')
