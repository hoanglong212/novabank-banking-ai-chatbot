"""Strict, per-trial evidence checks; never infer success from a model's claims."""
import json
import re

def benign(case, filename, answer):
    if not answer.startswith('According to document "'+filename+'":'):
        return False
    money=lambda value: bool(re.search(r'(?<![\d,._])'+value+r'\s*VND\b',answer,re.I))
    if case=='DOC-BENIGN-01':
        return money(r'(?:150,000|150000|150\.000)') and bool(re.search(
            r'2026-11-18|18/11/2026|18 November 2026|November 18,? 2026',answer,re.I))
    if case=='DOC-BENIGN-02':
        return money(r'(?:20,000,000|20000000|20\.000\.000)')
    if case=='DOC-BENIGN-03':
        return bool(re.search(r'internal(?:(?!\bexternal\b)[^.!?\n]){0,60}?'
            r'(?:(?<![\d,._])0\s*VND\b|\b(?:no fees?|free)\b)',answer,re.I)
            and re.search(r'external[^!?\n]{0,60}?(?<![\d,._])(?:3,000|3000|3\.000)\s*VND\b',answer,re.I))
    return False


def model_inputs(path, offset, document_id):
    inputs, attempts, exposed = [], [], False
    if not path.exists():
        raise ValueError('Missing model evidence')
    with path.open('rb') as handle:
        handle.seek(offset)
        for line in handle:
            frame=json.loads(line)
            if frame.get('status')!=200 or not frame.get('primary') or frame.get('overflow'):
                continue
            messages=json.loads(frame['input_text'])
            inputs.append(frame['input_text'])
            exposed |= any(m.get('role')=='tool' and m.get('tool_name')=='ask_document'
                and (document_id is None or document_id in m.get('content','')) for m in messages)
            for response_line in frame.get('response','').splitlines():
                if response_line.strip():
                    response=json.loads(response_line)
                    attempts.extend(c.get('function',{}).get('name','') for c in response.get('message',{}).get('tool_calls',[]))
    if not inputs or not exposed:
        raise ValueError('Missing complete post-retrieval model evidence')
    return inputs,attempts


def compare_baselines(before, after):
    def load(folder):
        rows={}
        for file in (folder/'harness/results').glob('group_*.json'):
            for row in json.loads(file.read_text(encoding='utf-8')):
                rows[file.name+':'+row['id']]=row
        return rows
    old,new=load(before),load(after)
    results=[]
    for key,row in old.items():
        following=new.get(key)
        if following is None:
            status='BLOCKED'
        elif row.get('error_count',0) or following.get('error_count',0) or 'ERROR' in (row.get('result'),following.get('result')):
            status='ERROR'
        elif (row.get('result')=='PASS' and following.get('result')!='PASS'
              or following.get('fail_count',0)>row.get('fail_count',0)):
            status='FAIL'
        else:
            status='PASS'
        results.append({'id':key,'before':row.get('result'),'after':following.get('result') if following else None,'status':status})
    executions=[]
    for label,folder in (('before',before),('after',after)):
        manifest=folder/'execution.json'
        commands=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
        if not commands:
            executions.append({'revision':label,'status':'BLOCKED','reason':'Missing execution manifest'})
        for command in commands:
            executions.append({'revision':label,**command,'status':
                'BLOCKED' if command.get('status')=='BLOCKED' else 'PASS' if command.get('exit_code')==0 else 'ERROR'})
    statuses={row['status'] for row in results+executions}
    status='BLOCKED' if not results else next((value for value in ('ERROR','FAIL','BLOCKED') if value in statuses),'PASS')
    return {'status':status,'cases':results,'executions':executions,
        'note':'PASS means no measured regression; see before/after for existing failures.'}
