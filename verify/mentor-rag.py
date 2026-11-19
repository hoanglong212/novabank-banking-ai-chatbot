"""Independent, benign Document RAG acceptance. Run with backend/.venv Python."""
import argparse
from contextlib import ExitStack, closing
from io import BytesIO
from itertools import product
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

import httpx
from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ('invoice', 'benign_invoice.pdf', 'What is the invoice total and the invoice date?'),
    ('rate_term', 'benign_loan_with_term.pdf', 'What are the annual interest rate and the term in months?'),
    ('term', 'benign_loan_contract.pdf', 'What is the length of the loan in months?'),
    ('fees', 'benign_fee_schedule.txt', 'What are the internal and external transfer fees in VND?'),
    ('absent', 'benign_invoice.pdf', 'What is the warranty period in years?'),
]


def expected(case, answer):
    if case == 'invoice':
        return bool(re.search(r'150[,. ]?000\s*VND', answer, re.I)
                    and re.search(r'2026-11-18|18[/-]11[/-]2026|Nov(?:ember)?\s+18,?\s+2026|18\s+Nov(?:ember)?\s+2026', answer, re.I))
    if case == 'rate_term':
        return bool(re.search(r'\b6\s*(?:%|percent)', answer, re.I) and re.search(r'\b24[ -]*months?\b', answer, re.I))
    if case == 'fees':
        return bool(re.search(r'internal[^.;\n]{0,70}\b0\s*VND|internal[^.;\n]{0,70}(free|no fee)', answer, re.I)
                    and re.search(r'external[^;\n]{0,70}3[,. ]?000\s*VND', answer, re.I))
    absence = re.search(r'could not verify an answer|not (?:explicitly )?(?:stated|mentioned|specified|provided|given)|does not (?:contain|provide|mention|specify)|no (?:information|details)|cannot (?:determine|find)', answer, re.I)
    guess = re.search(r'\b(?:\d+|one|two|three|six|twelve)[ -]+(?:months?|years?)\b|assum(?:e|ing)|it might be', answer, re.I)
    return bool(absence and not guess)


def stop(process):
    process.terminate()
    process.wait(timeout=20)


def observed_bank():
    """Pass through the real ASGI application, recording only typed test measurements."""
    from app.main import app
    evidence_file = Path(os.environ['MENTOR_RAG_OBSERVATIONS'])

    async def observe(scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/api/agent/tools':
            return await app(scope, receive, send)
        body = bytearray()

        async def record(event):
            if event['type'] == 'http.response.body':
                body.extend(event.get('body', b''))
                if not event.get('more_body') and body:
                    reply = json.loads(body)
                    result = reply.get('result')
                    if isinstance(result, dict) and 'document_id' in result and type(result.get('found')) is bool:
                        answer = result.get('answer')
                        evidence = {'hash':hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                                    'answer_empty':answer == '', 'matches':[]}
                        if isinstance(answer, str):
                            evidence['matches'] = [case for case, _, _ in CASES if expected(case, answer)]
                        with evidence_file.open('a', encoding='utf-8') as output:
                            output.write(json.dumps(evidence)+'\n')
            await send(event)
        return await app(scope, receive, record)
    return observe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repeats', type=int, choices=range(1,11), default=3)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', args.ref], cwd=ROOT, text=True).strip()
    profiles = {}
    files = {cfg:args.out.with_name(f'{args.out.stem}-{cfg}{args.out.suffix}') for cfg in 'DABC'}
    def persist(path, evidence):
        pending = path.with_suffix(path.suffix+'.tmp')
        pending.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        pending.replace(path)

    def checkpoint(cfg, profile):
        profiles[cfg] = profile
        persist(files[cfg], profile)
        # Keep the earlier single-campaign report shape for existing consumers.
        # D supplies the common API / UI probes; the sidecars retain every profile.
        aggregate = dict(profiles['D'])
        aggregate.pop('config', None)
        aggregate['probe_config']='D'
        aggregate['profile_files']={key:path.name for key,path in files.items()}
        aggregate['summary']={key:p['summary'] for key,p in profiles.items() if 'summary' in p}
        aggregate['cases']=[row for p in profiles.values() for row in p['cases']]
        aggregate['attempts']=[{**row,'config':key} for key,p in profiles.items() for row in p['attempts']]
        aggregate['finished']=len(profiles)==4 and all(p.get('finished') for p in profiles.values())
        persist(args.out, aggregate)

    for cfg in 'DABC':
        run_profile(sha,cfg,args.repeats,checkpoint)
    if len({p['business_fingerprint'] for p in profiles.values()})!=1:
        raise RuntimeError('Business seed differed between configurations')
    if any(any(row['status']!='PASS' for row in p['cases']) or p.get('deleted_question',{}).get('status')!='PASS' for p in profiles.values()):
        raise SystemExit(1)


def run_profile(sha,config,repeats,checkpoint):
    report = {'commit': sha, 'config':config, 'seed': 20261115, 'provider': 'ollama', 'models': {},
              'attempts': [], 'uploads': {}, 'api': {}, 'cases': [], 'repeats':repeats}

    def save():
        checkpoint(config,report)

    with tempfile.TemporaryDirectory(prefix='mentor-rag-', ignore_cleanup_errors=True) as tmp, ExitStack() as stack:
        folder = Path(tmp)
        src = folder / 'source'
        db = folder / 'bank.sqlite3'
        observations = folder/'document-measurements.jsonl'
        observations.touch()
        subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(src)], check=True)
        subprocess.run(['git', 'checkout', '-q', '--detach', sha], cwd=src, check=True)
        report['clean_checkout'] = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=src).strip()
        assert report['clean_checkout']
        oracle = {}
        for _, name, _ in CASES:
            path = src / 'fixtures' / 'documents' / name
            original = ' '.join(p.extract_text() for p in PdfReader(path).pages) if path.suffix == '.pdf' else path.read_text()
            if name == 'benign_invoice.pdf':
                oracle['invoice_total_and_date'] = '150,000 VND' in original and 'Invoice date: 2026-11-18' in original
            elif name == 'benign_loan_with_term.pdf':
                oracle['explicit_rate_and_term'] = 'Annual interest: 6 percent' in original and 'Contract term: 24 months' in original
            elif name == 'benign_loan_contract.pdf':
                oracle['rate'] = 'Annual interest: 6 percent' in original
                oracle['term_stated'] = bool(re.search(r'months|maturity|loan term|years', original, re.I))
            else:
                oracle['fee_pair'] = 'Internal transfers: 0 VND' in original and 'External transfers: 3,000 VND' in original
        report['source_oracle'] = oracle
        if oracle != {'invoice_total_and_date':True, 'explicit_rate_and_term':True, 'rate':True,
                      'term_stated':False, 'fee_pair':True}:
            raise ValueError('Benign fixture content differs from the campaign oracle')
        # Reserve a different loopback port for each child and keep the
        # reservations until launch. Refuse to use an existing listener.
        reserved = {}
        for service in ('bank','agent'):
            reserved[service]=stack.enter_context(socket.socket())
            reserved[service].bind(('127.0.0.1',0))
        bank_port=reserved['bank'].getsockname()[1]
        agent_port=reserved['agent'].getsockname()[1]
        bank_url = f'http://127.0.0.1:{bank_port}'
        agent_url = f'http://127.0.0.1:{agent_port}'
        env = dict(os.environ, ENV='demo', DB_PATH=str(db), PYTHONDONTWRITEBYTECODE='1',
                   LLM_PROVIDER='ollama', OLLAMA_URL='http://127.0.0.1:11434', OLLAMA_MODEL='qwen2.5:7b',
                   GUARD_MODEL='qwen2.5:7b', QUARANTINED_LLM_MODEL='llama3.2:3b',
                   EMBEDDING_MODEL='nomic-embed-text:latest', BANKING_API_URL=bank_url, AGENT_SERVICE_URL=agent_url,
                   BANK_REQUIRE_AGENT='true', BANK_WORKER_ENABLED='false', GATEWAY_MODE='local',
                   PROMPT_GUARD_MODEL_PATH=str(ROOT/'models/prompt-guard-2-86m'), PROMPT_GUARD_TIMEOUT_SECONDS='45')
        report['models'] = {key: env[key] for key in ('OLLAMA_MODEL','GUARD_MODEL','QUARANTINED_LLM_MODEL','EMBEDDING_MODEL','PROMPT_GUARD_TIMEOUT_SECONDS')}
        seed = subprocess.check_output([sys.executable, str(src/'scripts/seed_realistic.py'), '--output', str(db)],
                                       cwd=src, env=env, text=True)
        seed_info=json.loads(seed)
        report['seed_counts'] = seed_info['counts']
        report['business_fingerprint']=seed_info['business_fingerprint']
        save()
        for service,app,cwd,port in [('agent','agent_service.main:app',src,agent_port), ('bank','mentor-rag:observed_bank',src/'backend',bank_port)]:
            child_env = env.copy()
            if service == 'agent':
                child_env['PYTHONPATH'] = str(src/'backend')
                for key in ('DB_PATH','JWT_SECRET','QR_SIGNING_KEY','OTP_HASH_KEY','TRANSFER_TOKEN_KEY','MFA_ENCRYPTION_KEY'):
                    child_env.pop(key, None)
            else:
                child_env['PYTHONPATH']=str(src/'verify')
                child_env['MENTOR_RAG_OBSERVATIONS']=str(observations)
            reserved[service].close()
            startup_log = folder/(service+'.log')
            error_stream=stack.enter_context(startup_log.open('wb'))
            command=[sys.executable, '-m', 'uvicorn', app, '--host','127.0.0.1','--port',str(port),'--no-access-log']
            if service=='bank':
                command.append('--factory')
            child = subprocess.Popen(command,
                                     cwd=cwd, env=child_env, stdout=subprocess.DEVNULL, stderr=error_stream)
            stack.callback(stop, child)
            for _ in range(180):
                if child.poll() is not None:
                    raise RuntimeError(f'Disposable service {port} exited')
                try:
                    bound = f'Uvicorn running on http://127.0.0.1:{port}' in startup_log.read_text(encoding='utf-8', errors='replace')
                    if bound and httpx.get((agent_url+'/health' if service=='agent' else bank_url+'/api/health'), timeout=2, trust_env=False).status_code==200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError(f'Disposable service {port} unavailable')
        client = stack.enter_context(httpx.Client(base_url=bank_url, trust_env=False, timeout=180))
        conn = stack.enter_context(closing(sqlite3.connect(db)))
        conn.row_factory = sqlite3.Row

        def login(user):
            r = client.post('/api/auth/login', json={'username':user, 'password':user.capitalize()+'@2026'})
            r.raise_for_status()
            challenge = r.json()['challenge_id']
            message = client.post('/api/dev/outbox/challenge',json={'challenge_id':challenge})
            message.raise_for_status()
            r = client.post('/api/auth/mfa/verify',json={'challenge_id':challenge,'code':message.json()['code']})
            r.raise_for_status()
            return {'Authorization':'Bearer '+r.json()['access_token']}

        alice = login('alice')
        documents = {}
        for name in dict.fromkeys(name for _,name,_ in CASES):
            path = src/'fixtures/documents'/name
            for attempt in range(2):
                r = client.post('/api/documents', headers=alice, files={'file':(name,path.read_bytes())})
                r.raise_for_status()
                doc = r.json()
                report['attempts'].append({'upload':name,'attempt':attempt+1,'http':r.status_code,
                                           'status':doc['status'],'reason':doc['status_reason']})
                save()
                if doc['status']!='scan_failed':
                    break
                time.sleep(6)
            key = doc['id']
            row = conn.execute('SELECT owner_id,status,(SELECT COUNT(*) FROM doc_chunks WHERE document_id=d.id) chunks FROM documents d WHERE id=?',(key,)).fetchone()
            detail = client.get('/api/documents/'+key, headers=alice)
            items = client.get('/api/documents',headers=alice)
            present = any(item['id']==key for item in items.json()['items'])
            ok = (r.status_code==201 and items.status_code==detail.status_code==200 and present and 0<len(detail.json().get('preview',''))<=500
                  and row['owner_id']=='alice' and row['status']==doc['status']=='ready' and row['chunks']>0)
            report['uploads'][name] = dict(row) | {'passed':ok,'list_http':items.status_code,'listed':present,'detail_http':detail.status_code,
                                                    'valid_uuid4':uuid.UUID(key).version==4,'preview_length':len(detail.json().get('preview',''))}
            if ok:
                documents[name]=key
            save()

        report['api']['missing_token_get'] = client.get('/api/documents').status_code
        writer = PdfWriter()
        for _ in range(51):
            writer.add_blank_page(width=100,height=100)
        binary=BytesIO()
        writer.write(binary)
        invalid = [('image.png', b'\x89PNG\r\n\x1a\n', 'UNSUPPORTED_FILE'),('pages.pdf',binary.getvalue(),'TOO_MANY_PAGES'),
                   ('empty.txt',b'   ','NO_TEXT'),('large.txt',b'z'*(5*1024*1024+1),'FILE_TOO_LARGE')]
        for name, data, reason in invalid:
            r = client.post('/api/documents',headers=alice,files={'file':(name,data)})
            doc=r.json()
            dbrow=conn.execute('SELECT status_reason,(SELECT COUNT(*) FROM doc_chunks WHERE document_id=d.id) chunks FROM documents d WHERE id=?',(doc.get('id'),)).fetchone()
            report['api'][name]={'http':r.status_code,'state':doc.get('status'),'reason':doc.get('status_reason'),
                'db':dict(dbrow) if dbrow else None,'pass':r.status_code==201 and doc.get('status')=='rejected' and dbrow is not None and dbrow['status_reason']==doc.get('status_reason')==reason and dbrow['chunks']==0}
        save()

        def chat(name, question, key, config, case):
            r=client.post('/api/conversations',headers=alice,json={'title':'Mentor benign document check'})
            r.raise_for_status()
            cid=r.json()['id']
            r=client.post('/api/conversations/'+cid+'/stream',headers=alice,json={'content':'Document '+key+': '+question})
            events={}
            for line in r.text.splitlines():
                if line.startswith('event: '):
                    event=line[7:]
                elif line.startswith('data: '):
                    events[event]=json.loads(line[6:])
            answer=events.get('complete',{}).get('message',{}).get('content','')
            run=conn.execute('SELECT id,status,config FROM agent_runs WHERE conversation_id=? ORDER BY rowid DESC LIMIT 1',(cid,)).fetchone()
            calls=conn.execute('SELECT name,decision,reason,result_json FROM agent_calls WHERE run_id=? AND name=? ORDER BY rowid DESC LIMIT 1',(run['id'] if run else '', 'ask_document')).fetchone()
            result=json.loads(calls['result_json']) if calls and calls['result_json'] else {}
            cited=set(result.get('cited_chunk_ids',[]))
            sources={chunk['id']:chunk['text'] for chunk in conn.execute('SELECT id,text FROM doc_chunks WHERE document_id=? AND owner_id=?',(key,'alice'))}
            found=result.get('found')
            valid_cites=bool(cited) and cited<=sources.keys() and result.get('document_id')==key
            grounding=valid_cites and name in answer
            captured={entry['hash']:entry for entry in map(json.loads,observations.read_text(encoding='utf-8').splitlines())}
            observed=captured.get(result.get('sha256'))
            row={'config':config,'case':case,'http':r.status_code,'stream_events':list(events),'run':run['status'] if run else None,
                 'observed_config':run['config'] if run else None,'structured_hash_matches_db':observed is not None,
                 'decision':calls['decision'] if calls else None,'reason':calls['reason'] if calls else None,'found':found,
                 'citation_matches_source_and_filename':grounding,'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),
                 'display_observations':{'term_months':re.findall(r'\b(\d{1,3})[ -]*months?\b',answer,re.I),
                        'annual_six_percent':bool(re.search(r'\b6\s*(?:%|percent)',answer,re.I)),
                        'invoice_total_and_date':expected('invoice',answer),'fee_pair':expected('fees',answer),
                        'declares_absence_without_guess':expected('absent',answer)},
                 'cited_count':len(cited)}
            if case=='deleted':
                ok=calls is not None and calls['decision']=='DENY' and calls['reason']=='DOCUMENT_UNAVAILABLE' and not cited and '150,000' not in answer
            else:
                healthy=(r.status_code==200 and 'complete' in events and run is not None and run['status']=='COMPLETED'
                         and run['config']==config and row['decision']=='ALLOW')
                display_ok=healthy and expected(case,answer) and (case in ('term','absent') or name in answer)
                if case in ('term','absent'):
                    supported=found is False and not cited and observed is not None and observed['answer_empty']
                else:
                    cited_source='\n'.join(sources[source] for source in cited if source in sources)
                    supported=(found is True and valid_cites and expected(case,cited_source)
                               and observed is not None and case in observed['matches'])
                structured_ok=healthy and supported
                ok=display_ok and structured_ok
                row['display_status']='PASS' if display_ok else 'FAIL'
                row['structured_status']='PASS' if structured_ok else 'FAIL'
            infra=(r.status_code not in (200,400,404) or 'error' in events or row['reason'] in ('DOCUMENT_READER_UNAVAILABLE','DOCUMENT_RETRIEVAL_UNAVAILABLE')
                   or (run is not None and run['config']!=config) or (row['decision']=='ALLOW' and observed is None)
                   or (run is not None and run['status'] in ('ERROR','FAILED') and calls is None))
            row['status']='ERROR' if infra else 'PASS' if ok else 'FAIL'
            if infra:
                row['display_status']='ERROR'
                row['structured_status']='ERROR'
            return row

        admin=login('admin')
        alice=login('alice')
        r=client.put('/api/admin/agent-gateway',headers=admin,json={'config':config,'users':['alice'],'minutes':120})
        r.raise_for_status()
        assert r.json()['config']==config
        session_started=time.monotonic()
        for repeat,(case,name,question) in product(range(1,repeats+1),CASES):
            if name not in documents:
                report['cases'].append({'case':case,'config':config,'repeat':repeat,'status':'BLOCKED','reason':'upload not ready'})
                continue
            for attempt in range(2):
                if time.monotonic()-session_started>150:
                    alice=login('alice')
                    session_started=time.monotonic()
                try:
                    row=chat(name,question,documents[name],config,case)
                except httpx.HTTPError as error:
                    row={'config':config,'case':case,'status':'ERROR','reason':type(error).__name__}
                row['repeat']=repeat
                report['attempts'].append({k:v for k,v in row.items() if k!='answer'}|{'attempt':attempt+1})
                save()
                if row['status']!='ERROR':
                    break
                time.sleep(3)
                alice=login('alice')
                session_started=time.monotonic()
            report['cases'].append(row)
            print(config,repeat,case,row['status'],flush=True)
            save()
        key=documents.get('benign_invoice.pdf')
        if key:
            alice=login('alice')
            r=client.delete('/api/documents/'+key,headers=alice)
            gone=client.get('/api/documents/'+key,headers=alice)
            remaining=conn.execute('SELECT deleted_at IS NOT NULL,(SELECT count(*) FROM doc_chunks WHERE document_id=d.id) FROM documents d WHERE id=?',(key,)).fetchone()
            report['api']['delete']={'http':r.status_code,'body':r.json(),'detail_after':gone.status_code,'soft_deleted':bool(remaining[0]),'chunks_remaining':remaining[1]}
            report['deleted_question']=chat('benign_invoice.pdf','What is the invoice total?',key,config,'deleted')
        rows=report['cases']
        report['summary']={'n':len(rows), 'display_correct':sum(row.get('display_status')=='PASS' for row in rows),
                'structured_correct':sum(row.get('structured_status')=='PASS' for row in rows),'joint_correct':sum(row['status']=='PASS' for row in rows),
                'errors':sum(row['status']=='ERROR' for row in rows),
                'blocked':sum(row['status']=='BLOCKED' for row in rows)}
        report['finished']=True
        save()


if __name__=='__main__':
    main()
