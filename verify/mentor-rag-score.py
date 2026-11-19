"""Summarize captured HTTP/DB evidence, split displayed utility from tool metadata."""
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parents[1]/'docs/release/week8/verify-evidence'
live=json.loads((BASE/'rag-results.json').read_text(encoding='utf-8'))
api=json.loads((BASE/'rag-api.json').read_text(encoding='utf-8'))
ui=json.loads((BASE/'rag-ui.json').read_text(encoding='utf-8'))
assert live.get('finished') and len(live['cases'])==20
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
        if row['status'] in ('BLOCKED','ERROR'):
            display[case]=row['status']
            continue
        if case in ('term','absent'):
            healthy=(row['http']==200 and row['run']=='COMPLETED' and row['decision']=='ALLOW')
            display[case]='PASS' if healthy and absence_without_guess(case,row['answer']) else 'FAIL'
        else:
            display[case]=row['status']
    profiles[cfg]={'display':display,'display_correct':sum(value=='PASS' for value in display.values()),
        'structured_correct':sum(row['status']=='PASS' for row in rows),'denominator':len(rows)}

checks={}
b=data['DOC-API-01']
checks['DOC-API-01']=b['http']==201 and b['body_status']==b['db_status']=='ready' and b['hash_correct'] and b['detail']==200 and b['preview_present']
b=data['DOC-API-02']
checks['DOC-API-02']=b['anonymous_upload']==b['expired_http']==401
b=data['DOC-API-03']
checks['DOC-API-03']=b['http']==201 and b['status']=='rejected' and b['db_reason']==b['reason']=='UNSUPPORTED_FILE'
expected={'textless':'NO_TEXT','pages':'TOO_MANY_PAGES','encrypted':'ENCRYPTED_PDF','oversize':'FILE_TOO_LARGE'}
checks['DOC-API-04']=set(data['DOC-API-04'])==set(expected) and all(row['http']==201 and row['state']=='rejected' and row['reason']==row['db_reason']==expected[k] and row['chunks']==0 for k,row in data['DOC-API-04'].items())
b=data['DOC-API-05']
checks['DOC-API-05']=b['http']==201 and b['filename']=='Demo.txt'
b=data['DOC-API-06']
checks['DOC-API-06']=b['other_http']==[404,404] and all(item.get('detail')=='DOCUMENT_UNAVAILABLE' for item in b['other_body']) and b['owner_get']==200 and b['deleted_at'] is None and b['owner']=='bob' and b['chunk_count']>0
b=data['DOC-API-07']
checks['DOC-API-07']=b['valid_uuid4'] and not b['owner_file_visible_to_second_customer'] and b['absent_uuid_http']==404 and b['list_http']==200
b=data['DOC-API-08']
checks['DOC-API-08']=b['http']==201 and b['db_owner']=='alice'
b=data['DOC-API-09']
checks['DOC-API-09']=b['cap_http']==[201,409] and b['cap_body']=='DOCUMENT_LIMIT' and b['db_active_after']==20 and b['sequential_upload_statuses'][-1]==429
b=data['DOC-API-10']
checks['DOC-API-10']=b['delete']==200 and b['delete_body']=={'deleted':True} and b['detail_after']==404 and b['chunks_after']==0 and live.get('deleted_question',{}).get('status')=='PASS'
b=data['DOC-API-11']
checks['DOC-API-11']=b['anonymous_http']==401 and b['normal_customer_http'] in (401,403) and any(row.get('decision')=='ALLOW' for row in live['cases'])
b=data['DOC-API-12']
checks['DOC-API-12']=b['bad_media_http']==415 and b['bad_media_body']=={'detail':'MULTIPART_REQUIRED'} and not b['malformed_paths_or_traces']

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
