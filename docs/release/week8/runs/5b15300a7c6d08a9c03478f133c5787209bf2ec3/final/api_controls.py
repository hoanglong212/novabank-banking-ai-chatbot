"""Measure independent controls on disposable copies of the pinned synthetic application."""
import csv
import hashlib
import importlib
import json
import os
import random
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from pathlib import Path
from threading import Barrier, Thread

import httpx
import jwt
import uvicorn

OUT = Path(__file__).resolve().parent
SHA = OUT.parent.name
ROOT = next(p for p in OUT.parents if (p/'.git').exists())


@contextmanager
def serve(app):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False))
        worker = Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
        worker.start()
        try:
            deadline = time.monotonic()+30
            while not server.started:
                if not worker.is_alive() or time.monotonic()>deadline:
                    raise RuntimeError('Local server startup failed')
                time.sleep(.05)
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=30) as client:
                yield client
        finally:
            server.should_exit = True
            worker.join(30)


def auth_challenge(d):
    sessions = "SELECT COUNT(*) FROM user_sessions WHERE user_id='alice'"
    before = d.rows(sessions)
    challenge = d.call('POST','/api/auth/login',202,json={'username':'alice','password':'Alice@2026'})
    assert 'access_token' not in challenge
    for path in ('/api/me','/api/documents','/api/transactions'):
        d.call('GET',path,401,headers={'Authorization':'Bearer '+challenge['challenge_id']})
    after = d.rows(sessions)
    d.facts.update(sessions_before=before[0][0],sessions_after=after[0][0])
    assert before == after == [(0,)]


def owner(d):
    def snapshot():
        return dict(balances=d.totals(),drafts=d.rows('SELECT COUNT(*) FROM transfers')[0][0],
                    entries=d.rows('SELECT COUNT(*) FROM ledger_entries')[0][0])
    d.login()
    before = snapshot()
    response = d.call('POST','/api/transfers',400,json={'from_account':'ACC-BOB-001','to_account':'ACC-ALICE-001','amount_vnd':1000})
    after = snapshot()
    d.facts.update(before=before,after=after,reason=response.get('detail'))
    assert before==after and response.get('detail')=='ACCOUNT_NOT_OWNED'


def concurrent_spend(d):
    from app.dependencies import get_db
    from app.posting import post_journal
    from app.transfers import now
    d.login()
    d.known_payee()
    # Bring this synthetic account to a small, reconciled opening balance.
    # Both independent drafts must pass normal authorization before confirmation.
    with closing(get_db().connect()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        delta = d.totals()[0]-15000
        post_journal(conn,'FINAL-TEST-OPENING',[('ACC-ALICE-001',-delta),('SYS-OPENING',delta)],now())
        conn.commit()
    before = d.totals()
    drafts = [d.draft(10000),d.draft(10000)]
    assert drafts[0]['id']!=drafts[1]['id'] and before[0]==15000
    start = Barrier(2)
    def confirm(pair):
        ix, draft = pair
        start.wait(timeout=10)
        r=d.client.post('/api/transfers/'+draft['id']+'/confirm',
                        headers={**d.headers,'Idempotency-Key':'acceptance-'+str(ix)},
                        json={'otp':d.pin,'confirm_token':draft['confirm_token']})
        return [r.status_code,r.json().get('detail') or r.json().get('status')]
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(confirm,enumerate(drafts)))
    after = d.totals()
    ids = tuple(item['id'] for item in drafts)
    ledger=d.rows('SELECT COUNT(*),SUM(amount_vnd),COUNT(DISTINCT journal_id) FROM ledger_entries WHERE journal_id IN (?,?)',ids)[0]
    minimum=d.rows('SELECT MIN(balance_vnd) FROM accounts')[0][0]
    history=d.rows('SELECT COUNT(*) FROM transaction_details WHERE transfer_id IN (?,?)',ids)[0][0]
    d.facts.update(before=before,after=after,request_amounts=[10000,10000],http_confirm=results,
                   journal_rows=ledger[0],net_vnd=ledger[1],posted_drafts=ledger[2],history_rows=history,min_account_balance=minimum)
    assert sum(status==200 and reason=='COMPLETED' for status,reason in results)==1
    assert sum(400<=status<500 and reason=='INSUFFICIENT_FUNDS' for status,reason in results)==1
    assert after==[5000,before[1]+10000,before[2]] and minimum>=0 and ledger==(2,0,1) and history==2


def tokens(bank,agent):
    from app import auth
    from app.agent.agent_access import AUDIENCE
    now=int(time.time())
    claims=dict(iss=auth.ISSUER,aud=AUDIENCE,sub='acceptance-fixture',sid='unused',ver=1,
                run='unused',scope=[],iat=now-90,exp=now+60,tools=[],intent='0'*64,role='customer')
    # Only invalid fixtures are signed. The disposable process has its own key.
    invalid={'missing':None,'expired':jwt.encode(dict(claims,exp=now-60),auth.SECRET,algorithm='HS256'),
             'wrong_signature':jwt.encode(claims,secrets.token_bytes(48),algorithm='HS256'),
             'wrong_audience':jwt.encode(dict(claims,aud='other-test-service'),auth.SECRET,algorithm='HS256')}
    rows=[]
    for name,token in invalid.items():
        headers={'Authorization':'Bearer '+token} if token else {}
        bank_result=bank.get('/api/agent/context',headers=headers)
        result=agent.post('/run',headers=headers)
        rows.append(dict(variant=name,bank=bank_result.status_code,bank_reason=bank_result.json().get('detail'),agent=result.status_code))
    return {'status':'PASS' if all(row['bank']==row['agent']==401 and ('Invalid or expired' in row['bank_reason'] or row['variant']=='missing') for row in rows) else 'FAIL','observations':rows}


def spot(src,bank,agent):
    matrix=src/'docs/release/week8/verify-evidence/inventory-matrix.csv'
    with matrix.open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    seed=int(SHA[:12],16)
    checks=[]
    for row in random.Random(seed).sample(rows,10):
        client=bank if row['service']=='Bank' else agent
        path=re.sub(r'\{[^}]+\}','example',row['path'])
        response=client.options(path)
        actual={'GEN07':response.status_code}
        expected={'GEN07':int(row['GEN07'].split()[1])}
        if row['GEN02'].startswith('PASS '):
            actual['GEN02']=client.request(row['method'],path).status_code
            expected['GEN02']=int(row['GEN02'].split()[1])
        checks.append(dict(service=row['service'],method=row['method'],path=row['path'],actual=actual,expected=expected))
    return dict(seed=seed,population=len(rows),observations=checks,status='PASS' if all(x['actual']==x['expected'] for x in checks) else 'FAIL')


def seed_data(a,b):
    from app.identity import digest
    def measure(file):
        with closing(sqlite3.connect(file)) as conn:
            tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            hashes={}
            for table in tables:
                cols=[row[1] for row in conn.execute(f'PRAGMA table_info("{table}")') if (table,row[1])!=('users','password_hash')]
                fields=','.join('"'+k+'"' for k in cols)
                records=sorted(json.dumps(row,default=lambda x:x.hex()) for row in conn.execute(f'SELECT {fields} FROM "{table}"'))
                hashes[table]=hashlib.sha256('\n'.join(records).encode()).hexdigest()
            audits=conn.execute('SELECT id,created_at,report_json FROM reconciliation_runs ORDER BY id').fetchall()
            normalized_audits=[]
            for audit_id, stamp, report in audits:
                fields=json.loads(report)
                assert fields.pop('created_at')==stamp
                normalized_audits.append((audit_id,fields))
            business=dict(hashes,reconciliation_runs=hashlib.sha256(json.dumps(normalized_audits,sort_keys=True).encode()).hexdigest())
            login_locks = {r[0] for r in conn.execute('SELECT subject_hash FROM login_lockouts WHERE locked_until>0')}
            owners=[{'id':r[0],'status':r[1]} for r in conn.execute('SELECT id,status FROM users') if digest(r[0]) in login_locks]
            return hashes,[audits[0][1],json.loads(audits[0][2])['created_at']],owners,business
    first,t1,owners,first_business=measure(a)
    second,t2,_,second_business=measure(b)
    return dict(tables=len(first),different_tables=[k for k in first if first[k]!=second[k]],
                excluded=['users.password_hash'],timestamps=[t1,t2],locked_users=owners,
                hashes=[hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest() for m in (first,second)],
                business_without_audit_clock={'different_tables':[k for k in first_business if first_business[k]!=second_business[k]],
                  'additional_exclusions':['reconciliation_runs.created_at','reconciliation_runs.report_json.created_at']})


def main():
    data={'source_commit':SHA,'transport':'HTTP/1.1 on loopback','cases':{}}
    def save():
        (OUT/'api.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='nb-final-api-',ignore_cleanup_errors=True) as tmp:
        root=Path(tmp)
        src=root/'source'
        subprocess.run(['git','clone','-q','--shared','--no-checkout',str(ROOT),str(src)],check=True)
        subprocess.run(['git','-C',str(src),'checkout','-q','--detach',SHA],check=True)
        assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==SHA
        sys.path[:0]=[str(src/'verify'),str(src/'backend'),str(src)]
        os.chdir(src)
        os.environ.update(ENV='demo',BANK_WORKER_ENABLED='false',LLM_PROVIDER='mock',JWT_SECRET=secrets.token_urlsafe(48))
        a,b=[root/(x+'.sqlite3') for x in ('a','b')]
        for path in (a,b):
            subprocess.run([sys.executable,str(src/'scripts/seed_realistic.py'),'--output',str(path),'--seed','20261115'],check=True,stdout=subprocess.DEVNULL)
        data['seed']=seed_data(a,b)
        if sys.argv[1:]==['--seed-only']:
            (OUT/'seed-business.json').write_text(json.dumps({'source_commit':SHA,'seed':data['seed']},indent=2)+'\n',encoding='utf-8')
            return 0
        save()
        from app.main import app as bank_app
        Demo=importlib.import_module('mentor-bank').Demo
        for name,test in [('API-02',owner),('API-11',auth_challenge),('API-08',concurrent_spend)]:
            path=root/(name+'.sqlite3')
            shutil.copyfile(a,path)
            os.environ['DB_PATH']=str(path)
            with serve(bank_app) as bank:
                d=Demo(bank,path)
                try:
                    test(d)
                    status='PASS'
                except AssertionError as exc:
                    status='FAIL'
                    d.facts['error']=str(exc)
                except Exception as exc:
                    status='ERROR'
                    d.facts['error']=type(exc).__name__
                data['cases'][name]=dict(status=status,http=d.http,sql_results=d.facts)
                save()
        os.environ['DB_PATH']=str(b)
        with serve(bank_app) as bank:
            os.environ['BANKING_API_URL']=str(bank.base_url).rstrip('/')
            from agent_service.main import app as agent_app
            with serve(agent_app) as agent:
                data['cases']['Agent GEN-03']=tokens(bank,agent)
                data['cases']['inventory spot']=spot(src,bank,agent)
                save()
    return int(any(result['status'] != 'PASS' for result in data['cases'].values()))


if __name__=='__main__':
    sys.exit(main())
