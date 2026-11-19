"""Summarize captured HTTP/DB evidence, split displayed utility from tool metadata."""
import json
from pathlib import Path
import re
from mentor_doc_contracts import offline_checks
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parents[1]/'docs/release/week8/verify-evidence'
live=json.loads((BASE/'rag-results.json').read_text(encoding='utf-8'))
api=json.loads((BASE/'rag-api.json').read_text(encoding='utf-8'))
ui=json.loads((BASE/'rag-ui.json').read_text(encoding='utf-8'))
assert live.get('finished') and len(live['cases'])==20*live.get('repeats', 1)
assert api['commit']==ui['commit']==live['commit']
data=api['results']


def absence_without_guess(case, answer):
    evidence_of_absence=re.search(r"could not verify an answer|not (?:explicitly )?(?:stated|mentioned|specified|provided|given)|does not (?:contain|provide|mention|specify)|no (?:information|details)|cannot (?:determine|find)",answer,re.I)
    unsupported_duration=re.search(r"\b(?:\d+|one|two|three|six|twelve)(?:\s+|[-–])(?:months?|years?)\b",answer,re.I)
    return bool(evidence_of_absence and not unsupported_duration and not re.search(r'assum(?:e|ing)|it might be',answer,re.I))


profiles={}
for cfg in 'ABCD':
    rows=[row for row in live['cases'] if row['config']==cfg]
    display={}
    for row in rows:
        case=row['case']
        label=case if live.get('repeats',1)==1 else f"{case}/{row['repeat']}"
        if row['status'] in ('BLOCKED','ERROR'):
            display[label]=row['status']
            continue
        if row.get('display_status'):
            display[label]=row['display_status']
            continue
        if case in ('term','absent'):
            healthy=(row['http']==200 and row['run']=='COMPLETED' and row['decision']=='ALLOW')
            display[label]='PASS' if healthy and absence_without_guess(case,row['answer']) else 'FAIL'
        else:
            display[label]=row['status']
    profiles[cfg]={'display':display,'display_correct':sum(value=='PASS' for value in display.values()),
        'structured_correct':sum(row.get('structured_status',row['status'])=='PASS' for row in rows),
        'joint_correct':sum(row['status']=='PASS' for row in rows),'denominator':len(rows)}

checks = offline_checks(data)
checks['DOC-API-10'] = checks['DOC-API-10'] and live.get('deleted_question', {}).get('status') == 'PASS'
checks['DOC-API-11'] = checks['DOC-API-11'] and any(row.get('decision') == 'ALLOW' for row in live['cases'])

out={'commit':live['commit'],'api_observed':checks,'profiles':profiles,'browser':ui['results'],
     'coverage_note':'DOC-API-05 uses a benign nested HTML-like filename and reads the React text sink. DOC-API-07 uses a known foreign record and an unused UUID. DOC-API-11 is an ordinary credential denial plus a separate authorized question. No adversarial replay.'}
(BASE/'rag-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
suite=ET.Element('testsuite',name='Mentor independent document contracts and live structured answers')
def case(group,name,status,evidence):
    node=ET.SubElement(suite,'testcase',classname=group,name=name)
    tag={'FAIL':'failure','ERROR':'error','BLOCKED':'skipped'}.get(status)
    if tag:
        ET.SubElement(node,tag,message=status).text=json.dumps(evidence,ensure_ascii=False)
    ET.SubElement(node,'system-out').text=json.dumps(evidence,ensure_ascii=False)
for name,passed in checks.items():
    case('Document API',name,'PASS' if passed else 'FAIL',data[name])
for row in live['cases']:
    case('Document RAG '+row['config'],row['case'],row['status'],row)
for name,row in ui['results'].items():
    case('Document UI',name,'PASS' if row['visible'] else 'FAIL',row)
suite.set('tests',str(len(suite)))
for label,element in [('failures','failure'),('errors','error'),('skipped','skipped')]:
    suite.set(label,str(len(suite.findall('testcase/'+element))))
ET.indent(suite)
ET.ElementTree(suite).write(BASE/'rag-junit.xml',encoding='utf-8',xml_declaration=True)
print(json.dumps({'api':checks,'profiles':profiles},indent=2))
raise SystemExit(1 if any(int(suite.get(key)) for key in ('failures','errors','skipped')) else 0)
