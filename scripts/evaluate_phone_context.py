"""New synthetic evaluation, separate from development tests and old corpus."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.pii_patterns import phone_entities

cases=[
 ('Tổng: 0900000123 VND',[]),
 ('Phí 0910000234 đồng',[]),
 ('Chuyển 0920000345',[]),
 ('so tien: 0930000456',[]),
 ('Số dư 0940000567 đ',[]),
 ('Amount: 0950000678',[]),
 ('SĐT: 0900000123',['0900000123']),
 ('phone +84 910 000 234',['+84 910 000 234']),
 ('Gọi 092.000.0345',['092.000.0345']),
 ('dien thoai 093-000-0456',['093-000-0456']),
 ('Chuyển tiền rồi gọi 0940000567',['0940000567']),
 ('Số tiền 0950000678 VND, điện thoại 0960000789',['0960000789']),
]
rows=[]
for text,expected in cases:
    detected=[text[h.start:h.end] for h in phone_entities(text)]
    rows.append({'text':text,'expected':expected,'detected':detected,'pass':detected==expected})
output=ROOT/'docs/day2-evidence-2026-10-23/phone-context.json'
output.parent.mkdir(parents=True,exist_ok=True)
if output.exists():
    raise SystemExit('Evidence exists; choose a fresh output before rerunning')
report={'method':'12 new synthetic cases, not development tests; frozen context rule; no tuning after run',
        'cases':len(rows),'pass':sum(r['pass'] for r in rows),'rows':rows,
        'limitations':'Small templated sample; not a general Vietnamese PII guarantee; not production pipeline integration'}
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"Phone context: {report['pass']}/{report['cases']} cases passed")
