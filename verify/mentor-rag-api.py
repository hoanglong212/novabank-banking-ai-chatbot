"""Benign document HTTP/SQL contracts in a clean source checkout and fresh fixture DB."""
from contextlib import closing
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from unittest.mock import patch
from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('WEEK8_DOC_API_OUT', ROOT/'docs/release/week8/verify-evidence/rag-api.json'))


def verify(src, db):
    sys.path.insert(0,str(src/'backend'))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.documents.repository import Repository
    from app.dependencies import get_db
    results={}
    with TestClient(app,raise_server_exceptions=False) as client, closing(sqlite3.connect(db)) as conn:
        def login(user):
            response=client.post('/api/auth/login',json={'username':user,'password':user.capitalize()+'@2026'})
            response.raise_for_status()
            challenge=response.json()['challenge_id']
            otp=client.post('/api/dev/outbox/challenge',json={'challenge_id':challenge})
            otp.raise_for_status()
            session=client.post('/api/auth/mfa/verify',json={'challenge_id':challenge,'code':otp.json()['code']})
            session.raise_for_status()
            return {'Authorization':'Bearer '+session.json()['access_token']}

        alice,bob,charlie=[login(user) for user in ('alice','bob','charlie')]
        def post(headers, name, content, **kwargs):
            return client.post('/api/documents',headers=headers,files={'file':(name,content,'application/octet-stream')},**kwargs)

        real_pdf=(src/'fixtures/documents/benign_invoice.pdf').read_bytes()
        owned=post(bob,'benign_invoice.pdf',real_pdf)
        doc=owned.json()
        path='/api/documents/'+doc['id']
        saved=conn.execute('SELECT owner_id,status,sha256 FROM documents WHERE id=?',(doc['id'],)).fetchone()
        preview=client.get(path,headers=bob)
        results['DOC-API-01']={'http':owned.status_code,'body_status':doc['status'],'db_owner':saved[0],'db_status':saved[1],
            'hash_correct':saved[2]==hashlib.sha256(real_pdf).hexdigest(),'detail':preview.status_code,'preview_present':bool(preview.json().get('preview'))}
        missing=post({},'ordinary.txt',b'hello')
        with patch('app.auth.TTL_SECONDS',1):
            short_session=login('alice')
        time.sleep(2)
        expired=post(short_session,'ordinary.txt',b'hello')
        results['DOC-API-02']={'anonymous_upload':missing.status_code,'anonymous_body':missing.json(),'expired_http':expired.status_code,'expired_body':expired.json(),
                               'clock_fixture':'real sign-in with 1-second test TTL, then wait 2 seconds'}
        sample=post(alice,'fixture.pdf',b'MZ'+bytes(80))
        results['DOC-API-03']={'http':sample.status_code,'status':sample.json()['status'],'reason':sample.json()['status_reason'],
            'db_reason':conn.execute('SELECT status_reason FROM documents WHERE id=?',(sample.json()['id'],)).fetchone()[0],
            'input':'Inert header and zero bytes, no executable content'}
        materials={}
        for label,pages,encrypted in [('textless',1,False),('pages',51,False),('encrypted',1,True)]:
            writer=PdfWriter()
            for _ in range(pages):
                writer.add_blank_page(width=12,height=12)
            if encrypted:
                writer.encrypt('sample')
            buf=BytesIO()
            writer.write(buf)
            materials[label]=(label+'.pdf',buf.getvalue())
        materials['oversize']=('oversize.txt',b'A'*(5*1024*1024+1))
        results['DOC-API-04']={}
        for label,(name,data) in materials.items():
            r=post(alice,name,data)
            body=r.json()
            row=conn.execute('SELECT status_reason,(SELECT COUNT(*) FROM doc_chunks WHERE document_id=d.id) FROM documents d WHERE id=?',(body.get('id'),)).fetchone()
            results['DOC-API-04'][label]={'http':r.status_code,'reason':body.get('status_reason',body.get('detail')),
                'state':body.get('status'),'db_reason':row[0] if row else None,'chunks':row[1] if row else None}
        normalized=post(bob,'folder/<Demo>.txt',b'Synthetic sample file.')
        results['DOC-API-05']={'http':normalized.status_code,'filename':normalized.json().get('filename_display'),
                               'ui_source':'frontend/src/components/explore/Documents.tsx:88','browser_executed':False}
        denied=[client.request(method,path,headers=alice) for method in ('GET','DELETE')]
        positive=client.get(path,headers=bob)
        intact=conn.execute('SELECT owner_id,deleted_at,(SELECT COUNT(*) FROM doc_chunks WHERE document_id=d.id) FROM documents d WHERE id=?',(doc['id'],)).fetchone()
        results['DOC-API-06']={'other_http':[r.status_code for r in denied],'other_body':[r.json() for r in denied],
            'owner_get':positive.status_code,'owner':intact[0],'deleted_at':intact[1],'chunk_count':intact[2]}
        listing=client.get('/api/documents',headers=alice)
        results['DOC-API-07']={'valid_uuid4':uuid.UUID(doc['id']).version==4,'owner_file_visible_to_second_customer':any(r['id']==doc['id'] for r in listing.json()['items']),
                              'absent_uuid_http':client.get('/api/documents/'+str(uuid.uuid4()),headers=bob).status_code,'list_http':listing.status_code}
        extra=post(alice,'owned-note.txt',b'Sample public opening hours.',data={'owner_id':'bob'})
        results['DOC-API-08']={'http':extra.status_code,'db_owner':conn.execute('SELECT owner_id FROM documents WHERE id=?',(extra.json()['id'],)).fetchone()[0]}
        # Set a small, explicit precondition on the fresh DB. The boundary crossing itself goes through HTTP.
        repo=Repository(get_db(),'charlie')
        for i in range(19):
            repo.reserve(f'quota-{i}.txt','text/plain',8,hashlib.sha256(str(i).encode()).hexdigest())
        cap=[post(charlie,'limit.txt',b'An ordinary sample note.') for _ in range(2)]
        burst=[]
        for _ in range(11):
            r=post(bob,'empty.txt',b' ')
            burst.append(r.status_code)
            if r.status_code==429:
                break
        results['DOC-API-09']={'cap_http':[r.status_code for r in cap],'cap_body':cap[-1].json().get('detail'),'preexisting':19,
                               'db_active_after':conn.execute('SELECT COUNT(*) FROM documents WHERE owner_id=? AND deleted_at IS NULL',('charlie',)).fetchone()[0],
                               'sequential_upload_statuses':burst}
        delete=client.delete(path,headers=bob)
        results['DOC-API-10']={'delete':delete.status_code,'delete_body':delete.json(),'detail_after':client.get(path,headers=bob).status_code,
                              'chunks_after':conn.execute('SELECT COUNT(*) FROM doc_chunks WHERE document_id=?',(doc['id'],)).fetchone()[0]}
        anonymous=client.post('/api/agent/tools',json={'name':'ask_document','arguments':{}})
        ordinary_session=client.post('/api/agent/tools',headers=bob,json={'name':'ask_document','arguments':{}})
        results['DOC-API-11']={'anonymous_http':anonymous.status_code,'anonymous_body':anonymous.json(),'normal_customer_http':ordinary_session.status_code,
                               'normal_customer_body':ordinary_session.json(),'positive_gateway_case':'rag-results.json, ordinary user question; ask_document ALLOW'}
        bad=client.post('/api/documents',headers=charlie,json={})
        results['DOC-API-12']={'bad_media_http':bad.status_code,'bad_media_body':bad.json(),'auth_body':missing.json(),
                              'unavailable_body':denied[0].json(),'malformed_paths_or_traces':any('Traceback' in r.text or str(src) in r.text for r in [bad,missing,*denied])}
    return results


if __name__=='__main__':
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    with tempfile.TemporaryDirectory(prefix='mentor-docapi-',ignore_cleanup_errors=True) as tmp:
        folder=Path(tmp)
        src=folder/'source'
        subprocess.run(['git','clone','-q','--shared','--no-checkout',str(ROOT),str(src)],check=True)
        subprocess.run(['git','checkout','-q','--detach',sha],cwd=src,check=True)
        assert not subprocess.check_output(['git','status','--porcelain'],cwd=src).strip()
        db=folder/'demo.sqlite3'
        os.environ.update(ENV='demo',LLM_PROVIDER='mock',BANK_WORKER_ENABLED='false',GATEWAY_MODE='local',DB_PATH=str(db),PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable,str(src/'scripts/seed_realistic.py'),'--output',str(db)],cwd=src,stdout=subprocess.DEVNULL,check=True)
        out={'commit':sha,'clean':True,'seed':20261115,'provider':'explicit offline mock','results':verify(src,db)}
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(OUT)
