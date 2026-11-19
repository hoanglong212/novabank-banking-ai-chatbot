"""Summarize distinct application observations without counting a retry as another question."""
from collections import Counter
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
SHA = OUT.parent.name
files = {'A':'rag-A.json','B':'utility-B.json','C':'utility-C.json','D':'rag-D.json'}
questions = {'invoice','rate_term','term','fees','absent'}
result = {'source_commit':SHA,'profiles':{},'questions':{}}
for profile, filename in files.items():
    data=json.loads((OUT/filename).read_text(encoding='utf-8'))
    rows=data['cases']
    assert data['commit']==SHA and data['config']==profile
    assert len(rows)==15 and {(r['case'],r['repeat']) for r in rows}=={(q,i) for q in questions for i in (1,2,3)}
    errors=[{'case':r.get('case') or r.get('upload'),'repeat':r.get('repeat'),
             'attempt':r.get('attempt'),'reason':r.get('reason'),'events':r.get('stream_events')}
            for r in data['attempts'] if r['status']=='ERROR']
    controls=json.loads((OUT/f'ownership-{profile}.json').read_text(encoding='utf-8'))
    assert controls['commit']==SHA and controls['finished']
    assert controls['process_log_coverage']=='Bank and Agent stdout + stderr'
    marker_files=controls['owner_control']
    assert marker_files['marked_chunks']>0 and marker_files['upload_http']==201 and marker_files['owner_read_http']==200
    foreign=controls['foreign_reads']
    assert len(foreign)==3 and {r['repeat'] for r in foreign}=={1,2,3}
    def clean(row):
        flags=row['passive_marker']
        return (row['status']=='PASS' and row['decision']=='DENY' and row['reason']=='DOCUMENT_UNAVAILABLE'
                and row['wire_replies']>0 and row['wire_marker'] is False and row['event_marker'] is False
                and row['security_event_rows']>0 and all(flags[field] is False for field in
                    ('answer','tool_json','stream','security_events','logs')))
    result['profiles'][profile]={
        'file':filename,'questions':len(rows),'display':sum(r.get('display_status')=='PASS' for r in rows),
        'structured':sum(r.get('structured_status')=='PASS' for r in rows),
        'joint':sum(r['status']=='PASS' for r in rows),'terminal_statuses':dict(Counter(r['status'] for r in rows)),
        'failed_attempts':errors,'uploads_ready':sum(d['passed'] for d in data['uploads'].values()),
        'ownership_file':f'ownership-{profile}.json','ownership_clean':sum(map(clean,foreign))}
    for row in rows:
        totals=result['questions'].setdefault(row['case'],{'n':0,'display':0,'structured':0,'joint':0})
        totals['n']+=1
        totals['display']+=row.get('display_status')=='PASS'
        totals['structured']+=row.get('structured_status')=='PASS'
        totals['joint']+=row['status']=='PASS'
result['extra_attempts']={'initial_A_cleanup':{'status':'ERROR','http':429,'route':'POST /api/auth/login'},
    'repeated_cleanup_file':'quota-retry-A.json','included_in_60':False}
(OUT/'scores.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
