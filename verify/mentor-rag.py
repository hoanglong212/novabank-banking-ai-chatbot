"""Independent, benign Document RAG acceptance. Run with backend/.venv Python."""
import argparse
from contextlib import ExitStack, closing
from io import BytesIO
import json
import os
from pathlib import Path
import re
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
    ('rate', 'benign_loan_contract.pdf', 'What is the annual interest rate?'),
    ('term', 'benign_loan_contract.pdf', 'What is the length of the loan in months?'),
    ('fees', 'benign_fee_schedule.txt', 'What are the internal and external transfer fees in VND?'),
    ('absent', 'benign_invoice.pdf', 'What is the warranty period in years?'),
]


def expected(case, answer):
    if case == 'invoice':
        return bool(re.search(r'150[,. ]?000\s*VND', answer, re.I)
                    and re.search(r'2026-11-18|18[/-]11[/-]2026|Nov(?:ember)?\s+18,?\s+2026|18\s+Nov(?:ember)?\s+2026', answer, re.I))
    if case == 'rate':
        return bool(re.search(r'\b6\s*(?:%|percent)', answer, re.I))
    if case == 'fees':
        return bool(re.search(r'internal[^.;\n]{0,70}\b0\s*VND|internal[^.;\n]{0,70}(free|no fee)', answer, re.I)
                    and re.search(r'external[^;\n]{0,70}3[,. ]?000\s*VND', answer, re.I))
    return 'could not verify an answer' in answer.lower()


def stop(process):
    process.terminate()
    process.wait(timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(['git', 'rev-parse', args.ref], cwd=ROOT, text=True).strip()
    report = {'commit': sha, 'seed': 20261115, 'provider': 'ollama', 'models': {},
              'attempts': [], 'uploads': {}, 'api': {}, 'cases': []}

    def save():
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    with tempfile.TemporaryDirectory(prefix='mentor-rag-', ignore_cleanup_errors=True) as tmp, ExitStack() as stack:
        folder = Path(tmp)
        src = folder / 'source'
        db = folder / 'bank.sqlite3'
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
            elif name == 'benign_loan_contract.pdf':
                oracle['rate'] = 'Annual interest: 6 percent' in original
                oracle['term_stated'] = bool(re.search(r'months|maturity|loan term|years', original, re.I))
            else:
                oracle['fee_pair'] = 'Internal transfers: 0 VND' in original and 'External transfers: 3,000 VND' in original
        report['source_oracle'] = oracle
        bank_url = 'http://127.0.0.1:18211'
        agent_url = 'http://127.0.0.1:18214'
        env = dict(os.environ, ENV='demo', DB_PATH=str(db), PYTHONDONTWRITEBYTECODE='1',
                   LLM_PROVIDER='ollama', OLLAMA_URL='http://127.0.0.1:11434', OLLAMA_MODEL='qwen2.5:7b',
                   GUARD_MODEL='qwen2.5:7b', QUARANTINED_LLM_MODEL='llama3.2:3b',
                   EMBEDDING_MODEL='nomic-embed-text:latest', BANKING_API_URL=bank_url, AGENT_SERVICE_URL=agent_url,
                   BANK_REQUIRE_AGENT='true', BANK_WORKER_ENABLED='false', GATEWAY_MODE='local',
                   PROMPT_GUARD_MODEL_PATH=str(ROOT/'models/prompt-guard-2-86m'), PROMPT_GUARD_TIMEOUT_SECONDS='45')
        report['models'] = {key: env[key] for key in ('OLLAMA_MODEL','GUARD_MODEL','QUARANTINED_LLM_MODEL','EMBEDDING_MODEL','PROMPT_GUARD_TIMEOUT_SECONDS')}
        seed = subprocess.check_output([sys.executable, str(src/'scripts/seed_realistic.py'), '--output', str(db)],
                                       cwd=src, env=env, text=True)
        report['seed_counts'] = json.loads(seed)['counts']
        save()
        for app, cwd, port in [('agent_service.main:app',src,18214), ('app.main:app',src/'backend',18211)]:
            child_env = env.copy()
            if port == 18214:
                child_env['PYTHONPATH'] = str(src/'backend')
                for key in ('DB_PATH','JWT_SECRET','QR_SIGNING_KEY','OTP_HASH_KEY','TRANSFER_TOKEN_KEY','MFA_ENCRYPTION_KEY'):
                    child_env.pop(key, None)
            child = subprocess.Popen([sys.executable, '-m', 'uvicorn', app, '--host','127.0.0.1','--port',str(port)],
                                     cwd=cwd, env=child_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            stack.callback(stop, child)
            for _ in range(180):
                if child.poll() is not None:
                    raise RuntimeError(f'Disposable service {port} exited')
                try:
                    if httpx.get((agent_url+'/health' if port==18214 else bank_url+'/api/health'), timeout=2).status_code==200:
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

        admin = login('admin')
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
            run=conn.execute('SELECT id,status FROM agent_runs WHERE conversation_id=? ORDER BY rowid DESC LIMIT 1',(cid,)).fetchone()
            calls=conn.execute('SELECT name,decision,reason,result_json FROM agent_calls WHERE run_id=? AND name=? ORDER BY rowid DESC LIMIT 1',(run['id'] if run else '', 'ask_document')).fetchone()
            result=json.loads(calls['result_json']) if calls and calls['result_json'] else {}
            cited=set(result.get('cited_chunk_ids',[]))
            source_ids={row[0] for row in conn.execute('SELECT id FROM doc_chunks WHERE document_id=?',(key,))}
            found=result.get('found')
            grounding=bool(cited) and cited<=source_ids and name in answer
            row={'config':config,'case':case,'http':r.status_code,'stream_events':list(events),'run':run['status'] if run else None,
                 'decision':calls['decision'] if calls else None,'reason':calls['reason'] if calls else None,'found':found,
                 'citation_matches_source_and_filename':grounding,'answer':answer[:700],'cited_count':len(cited)}
            if case=='deleted':
                ok=calls is not None and calls['decision']=='DENY' and calls['reason']=='DOCUMENT_UNAVAILABLE' and not cited and '150,000' not in answer
            else:
                ok=(r.status_code==200 and run is not None and run['status']=='COMPLETED' and row['decision']=='ALLOW'
                    and expected(case,answer) and ((found is False and not cited) if case in ('term','absent') else found is True and grounding))
            infra=(r.status_code not in (200,400,404) or 'error' in events or row['reason'] in ('DOCUMENT_READER_UNAVAILABLE','DOCUMENT_RETRIEVAL_UNAVAILABLE')
                   or (run is not None and run['status'] in ('ERROR','FAILED') and calls is None))
            row['status']='ERROR' if infra else 'PASS' if ok else 'FAIL'
            return row

        for config in ('D','A','B','C'):
            admin=login('admin')
            alice=login('alice')
            r=client.put('/api/admin/agent-gateway',headers=admin,json={'config':config,'users':['alice']})
            r.raise_for_status()
            assert r.json()['config']==config
            for case,name,question in CASES:
                if name not in documents:
                    report['cases'].append({'case':case,'config':config,'status':'BLOCKED','reason':'upload not ready'})
                    continue
                for attempt in range(2):
                    try:
                        row=chat(name,question,documents[name],config,case)
                    except httpx.HTTPError as error:
                        row={'config':config,'case':case,'status':'ERROR','reason':type(error).__name__}
                    report['attempts'].append({k:v for k,v in row.items() if k!='answer'}|{'attempt':attempt+1})
                    save()
                    if row['status']!='ERROR':
                        break
                    time.sleep(3)
                    alice=login('alice')
                report['cases'].append(row)
                print(config,case,row['status'],flush=True)
                save()
        key=documents.get('benign_invoice.pdf')
        if key:
            r=client.delete('/api/documents/'+key,headers=alice)
            gone=client.get('/api/documents/'+key,headers=alice)
            remaining=conn.execute('SELECT deleted_at IS NOT NULL,(SELECT count(*) FROM doc_chunks WHERE document_id=d.id) FROM documents d WHERE id=?',(key,)).fetchone()
            report['api']['delete']={'http':r.status_code,'body':r.json(),'detail_after':gone.status_code,'soft_deleted':bool(remaining[0]),'chunks_remaining':remaining[1]}
            report['deleted_question']=chat('benign_invoice.pdf','What is the invoice total?',key,'C','deleted')
        report['finished']=True
        save()


if __name__=='__main__':
    main()
