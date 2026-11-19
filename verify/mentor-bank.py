"""Run ordinary banking acceptance cases against isolated TestClient instances and copied seed DBs."""
import argparse
import base64
import gc
from contextlib import closing
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import patch
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient


def check(condition, description):
    if not condition:
        raise AssertionError(description)


def totp(secret, step):
    mac=hmac.digest(base64.b32decode(secret),step.to_bytes(8,'big'),hashlib.sha1)
    offset=mac[-1]&15
    return f'{(int.from_bytes(mac[offset:offset+4],"big")&0x7fffffff)%1000000:06d}'


class Demo:
    def __init__(self, client, db):
        self.client=client
        self.db=db
        self.headers={}
        self.http=[]
        self.facts={}
        self.pin='48'+str(secrets.randbelow(10000)).zfill(4)

    def rows(self, sql, params=()):
        with closing(sqlite3.connect(self.db.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
            return conn.execute(sql,params).fetchall()

    def call(self, method, path, expected, **kwargs):
        r=self.client.request(method,path,headers=kwargs.pop('headers',self.headers),**kwargs)
        self.http.append([method,path.split('?')[0],r.status_code])
        if r.status_code>=500 or (r.status_code==429 and expected!=429):
            raise RuntimeError(f'Unexpected service error {r.status_code}')
        check(r.status_code==expected,f'{method} {path}: expected {expected}, got {r.status_code}')
        return r.json() if r.content else {}

    def login(self, user='alice'):
        challenge=self.call('POST','/api/auth/login',202,json={'username':user,'password':user.title()+'@2026'})
        check('access_token' not in challenge,'Access token before MFA')
        self.call('GET','/api/me',401,headers={})
        body={'challenge_id':challenge['challenge_id']}
        code=self.call('POST','/api/dev/outbox/challenge',200,json=body)['code']
        self.session=self.call('POST','/api/auth/mfa/verify',200,json={**body,'code':code})
        self.headers={'Authorization':'Bearer '+self.session['access_token']}
        self.call('GET','/api/me',200)

    def totals(self):
        return [self.rows('SELECT balance_vnd FROM accounts WHERE id=?',(a,))[0][0] for a in
                ('ACC-ALICE-001','ACC-BOB-001')]+[self.rows('SELECT SUM(balance_vnd) FROM accounts')[0][0]]

    def draft(self, amount, **kwargs):
        return self.call('POST','/api/transfers',201,json={'from_account':'ACC-ALICE-001',
            'to_account':'ACC-BOB-001','amount_vnd':amount,**kwargs})

    def confirm(self,draft,code,key,expected=200):
        return self.call('POST','/api/transfers/'+draft['id']+'/confirm',expected,
            headers={**self.headers,'Idempotency-Key':key},json={'otp':code,'confirm_token':draft['confirm_token']})

    def enroll(self):
        secret=self.call('POST','/api/auth/mfa/setup',200,json={'password':'Alice@2026'})['secret']
        self.call('POST','/api/auth/mfa/enable',200,json={'code':totp(secret,int(time.time())//30-1)})
        return secret

    def known_payee(self):
        secret=self.enroll()
        self.call('POST','/api/auth/pin',200,json={'password':'Alice@2026','pin':self.pin})
        first=self.draft(1000)
        path='/api/transfers/'+first['id']
        self.call('POST',path+'/step-up',200,json={'code':totp(secret,int(time.time())//30)})
        emailed=self.call('POST',path+'/otp',200)
        check(emailed['otp_method']=='email','Expected new-payee email')
        code=self.rows('SELECT secret_text FROM dev_outbox WHERE user_id=? AND challenge_id=? ORDER BY rowid DESC LIMIT 1',
                       ('alice','transfer:'+first['id']))[0][0]
        check(self.confirm(emailed,code,'mentor-first-payment')['status']=='COMPLETED','New payee not settled')


def accounts(d):
    d.login()
    me=d.call('GET','/api/me',200)
    expected=dict(d.rows("SELECT id,balance_vnd FROM accounts WHERE owner_id='alice'"))
    check({r['id']:r['balance_vnd'] for r in me['accounts']}==expected,'Account list or balance differs')
    history=d.rows("""SELECT t.id,t.amount_vnd,t.direction FROM transactions t JOIN accounts a ON a.id=t.account_id
                      WHERE a.owner_id='alice' ORDER BY t.date DESC,t.created_at DESC,t.id DESC""")
    for pos in (0,5,len(history)-1,len(history)):
        page=d.call('GET',f'/api/transactions?limit=5&offset={pos}',200)
        check([(r['id'],r['amount_vnd'],r['direction']) for r in page['items']]==history[pos:pos+5],'Page differs')
    for direction in ('in','out'):
        page=d.call('GET','/api/transactions?limit=5&direction='+direction,200)
        check([r['id'] for r in page['items']]==[r[0] for r in history if r[2]==direction][:5],'Filter differs')
    found=d.call('GET','/api/transactions?q='+history[0][0],200)
    check([r['id'] for r in found['items']]==[history[0][0]],'Search differs')
    d.facts.update(accounts=len(expected),history=len(history),first_amounts=[x[1] for x in history[:5]])


def auth(d):
    d.login()
    d.call('POST','/api/auth/logout',200)
    d.call('GET','/api/me',401)
    check(d.rows('SELECT revoked_at FROM user_sessions WHERE id=?',(d.session['session_id'],))[0][0] is not None,'Session not revoked')
    errors=[d.call('POST','/api/auth/login',401,json={'username':u,'password':'wrong-password'})
            for u in ('alice','missing-mentor-fixture')]
    check(errors[0]==errors[1],'Different login errors')


def expiry(d):
    from app import auth
    lifetime=auth.TTL_SECONDS
    try:
        auth.TTL_SECONDS=3
        d.login()
        time.sleep(4)
        d.call('GET','/api/me',401)
    finally:
        auth.TTL_SECONDS=lifetime
    rotated=d.call('POST','/api/auth/refresh',200,json={'refresh_token':d.session['refresh_token']})
    d.headers={'Authorization':'Bearer '+rotated['access_token']}
    d.call('GET','/api/me',200)
    check(rotated['refresh_token']!=d.session['refresh_token'],'Refresh did not rotate')


def factor(d):
    d.login()
    secret=d.enroll()
    check(d.call('GET','/api/auth/mfa',200)['totp_enabled'],'TOTP not enabled')
    challenge=d.call('POST','/api/auth/mfa/disable-request',200,json={'password':'Alice@2026'})
    if challenge.get('method')=='totp':
        code=totp(secret,int(time.time())//30)
    else:
        items=d.call('GET','/api/dev/outbox',200)['items']
        item=next(r for r in items if 'DISABLE' in r['kind'])
        code=d.call('GET','/api/dev/outbox/'+item['id'],200)['code']
    d.call('POST','/api/auth/mfa/disable',200,json={'challenge_id':challenge['challenge_id'],'code':code})
    check(not d.call('GET','/api/auth/mfa',200)['totp_enabled'],'TOTP still active')


def payment(d):
    d.login('bob')
    qr=d.call('POST','/api/vietqr',200,json={'bank':'NovaBank','account_no':'ACC-BOB-001','amount_vnd':11000})
    check(qr['account_no']=='ACC-BOB-001' and qr['amount_vnd']==11000 and qr['image'],'QR creation mismatch')
    d.login()
    qr=d.call('POST','/api/qr/decode',200,json={'payload':qr['payload']})
    check(qr['account_no']=='ACC-BOB-001' and qr['amount_vnd']==11000,'QR decode mismatch')
    d.known_payee()
    before=d.totals()
    draft=d.draft(qr['amount_vnd'],to_account=qr['account_no'],source_origin=qr['source_origin'])
    check(d.totals()==before and draft['otp_method']=='pin','Draft posted or wrong factor')
    receipt=d.confirm(draft,d.pin,'mentor-qr-receipt')
    check(receipt['status']=='COMPLETED' and d.confirm(draft,d.pin,'mentor-qr-receipt')==receipt,'Duplicate receipt differs')
    after=d.totals()
    fee=draft['fee_vnd']
    check(after==[before[0]-11000-fee,before[1]+11000,before[2]-fee],'Incorrect final balances')
    legs=d.rows('SELECT account_id,amount_vnd FROM ledger_entries WHERE journal_id=? ORDER BY account_id',(draft['id'],))
    history=d.rows('SELECT t.account_id,t.direction,t.amount_vnd FROM transactions t JOIN transaction_details d ON d.transaction_id=t.id WHERE d.transfer_id=? ORDER BY t.account_id',(draft['id'],))
    check(history==[('ACC-ALICE-001','out',11000),('ACC-BOB-001','in',11000)],'Missing or duplicate history')
    check(sum(x[1] for x in legs)==0 and len(legs)==2,'Journal unbalanced or duplicated')
    d.facts.update(before=before,after=after,journal=legs,transactions=history,fee=fee)
    second=d.draft(12000)
    denied=d.confirm(second,d.pin,'mentor-qr-receipt',409)
    check(denied['detail']=='IDEMPOTENCY_CONFLICT' and d.totals()==after,'Changed request posted')


def invalid(d):
    d.login()
    d.call('POST','/api/auth/pin',200,json={'password':'Alice@2026','pin':d.pin})
    before=d.totals()
    for recipient,amount,reason in [('ACC-ALICE-001',1000,'SAME_ACCOUNT'),('ACC-NO-SUCH-DEMO',1000,'RECIPIENT_NOT_FOUND'),
                                   ('ACC-BOB-001',before[0]+1000,'INSUFFICIENT_FUNDS')]:
        body={'from_account':'ACC-ALICE-001','to_account':recipient,'amount_vnd':amount}
        check(d.call('POST','/api/transfers',400,json=body)['detail']==reason,reason)
    for amount in (-1,0,1.234,'1000',None,100000001):
        d.call('POST','/api/transfers',422,json={'to_account':'ACC-BOB-001','amount_vnd':amount})
    check(before==d.totals(),'Rejected request changed balances')
    d.facts.update(balances=before,invalid_amount_http=422,api04_expected=[400,422])


def lock_and_expiry(d):
    from app import transfers
    d.login()
    d.known_payee()
    draft=d.draft(4000)
    before=d.totals()
    wrong='01'+d.pin[2:]
    check(d.confirm(draft,wrong,'mentor-pin-check',400)['detail']=='OTP_INVALID','Wrong PIN not rejected')
    # Prime the failure counter to exercise the lock threshold without guessing credentials.
    with closing(sqlite3.connect(d.db)) as conn:
        conn.execute("UPDATE transaction_pins SET failures=4 WHERE user_id='alice'")
        conn.commit()
    check(d.confirm(draft,wrong,'mentor-pin-limit',423)['detail']=='PIN_LOCKED','Temporary lock missing')
    until=d.rows("SELECT locked_until FROM transaction_pins WHERE user_id='alice'")[0][0]
    check(until>time.time() and d.totals()==before,'Lock state or balances incorrect')
    future=(datetime.fromisoformat(draft['expires_at'])+timedelta(seconds=2)).isoformat()
    with patch.object(transfers,'now',return_value=future):
        expired=d.confirm(draft,d.pin,'mentor-expiry',403)
    check(expired['detail']=='TOKEN_EXPIRED' and d.totals()==before,'Expired request posted')
    d.facts.update(lock_seconds_remaining=round(until-time.time()),after=d.totals(),expiry_reason=expired['detail'])


def rate_window(d):
    from app import identity
    path='/api/auth/login'
    now=identity.timestamp()
    start=now-now%900
    with closing(sqlite3.connect(d.db)) as conn:
        conn.execute('INSERT INTO identity_limits VALUES (?,?,?,?)',('request:'+path,identity.digest('testclient'),start,20))
        conn.commit()
    credentials={'username':'bob','password':'Bob@2026'}
    with patch.object(identity,'timestamp',return_value=now):
        d.call('POST',path,429,json=credentials)
    with patch.object(identity,'timestamp',return_value=start+901):
        d.call('POST',path,202,json=credentials)
    d.facts['request_counts']=d.rows('SELECT attempts FROM identity_limits WHERE scope=? ORDER BY starts_at',('request:'+path,))


def metadata(d):
    d.login()
    d.call('GET','/api/transactions?limit=100000',422)
    page=d.call('GET','/api/transactions?page=-1',200)
    check(len(page['items'])<=100 and len(page['items'])<page['total'],'Unbounded page')
    bad=d.call('POST','/api/qr/decode',422,json={'payload':'not a demo QR'})
    check(isinstance(bad['detail'],str) and len(bad['detail'])<160,'Unclear QR error')
    own=d.call('GET','/api/transactions?account_id=ACC-ALICE-001',200)
    check(own['items'] and all(r['account_id']=='ACC-ALICE-001' for r in own['items']),'Owner read missing')
    denied=d.call('GET','/api/transactions?account_id=ACC-BOB-001',404)
    check(set(denied)=={'detail'},'Expected generic denial')
    for origin,expected in [('http://localhost:5173',200),('https://unlisted.invalid',400)]:
        res=d.client.options('/api/transfers',headers={'Origin':origin,'Access-Control-Request-Method':'POST'})
        check(res.status_code==expected and res.headers.get('access-control-allow-origin')==(origin if expected==200 else None),'CORS mismatch')
        d.http.append(['OPTIONS','/api/transfers',res.status_code])
    d.facts.update(negative_page_count=len(page['items']),negative_page_total=page['total'])


CASES={'accounts':accounts,'login/logout':auth,'expiry/refresh':expiry,'TOTP enable/disable':factor,
       'PIN/QR/idempotency':payment,'invalid transfer':invalid,'paging/QR/owner/CORS':metadata,
       'PIN lock and draft expiry':lock_and_expiry,'quota window':rate_window}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clone',type=Path,help='Existing clean checkout; defaults to a local clone of the audited commit.')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.clone is None:
        workspace=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='mentor-src-') as tmp:
            checkout=Path(tmp)/'source'
            subprocess.run(['git','clone','--quiet','--no-hardlinks','--no-checkout',str(workspace),str(checkout)],check=True)
            subprocess.run(['git','-C',str(checkout),'checkout','--quiet','--detach',subprocess.check_output(['git','-C',str(workspace),'rev-parse','HEAD'],text=True).strip()],check=True)
            return subprocess.run([sys.executable,__file__,'--clone',str(checkout),'--out',str(args.out.resolve())]).returncode
    root=args.clone.resolve()
    rev=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain']).strip():
        raise SystemExit('Supply a clean checkout')
    os.environ.update(ENV='demo',LLM_PROVIDER='mock',BANK_WORKER_ENABLED='false',CORS_ORIGINS='http://localhost:5173')
    sys.path.insert(0,str(root/'backend'))
    results={}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mentor-func-') as tmp:
        seed=Path(tmp)/'seed.sqlite3'
        os.environ['DB_PATH']=str(seed)
        subprocess.run([sys.executable,str(root/'scripts/seed_realistic.py'),'--output',str(seed)],check=True,stdout=subprocess.DEVNULL)
        from app.main import app
        for index,(name,case) in enumerate(CASES.items()):
            db=Path(tmp)/f'case-{index}.sqlite3'
            shutil.copyfile(seed,db)
            os.environ['DB_PATH']=str(db)
            with TestClient(app,raise_server_exceptions=False) as client:
                d=Demo(client,db)
                try:
                    case(d)
                    result={'status':'PASS'}
                except (AssertionError,RuntimeError,KeyError,StopIteration) as exc:
                    result={'status':'FAIL' if isinstance(exc,AssertionError) else 'ERROR','detail':str(exc),'type':type(exc).__name__}
                results[name]={**result,'http':d.http,'facts':d.facts}
                print(name,result,flush=True)
            gc.collect()
            args.out.write_text(json.dumps({'commit':rev,'seed':20261115,'cases':results},indent=2)+'\n',encoding='utf-8')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps({'commit':rev,'seed':20261115,'cases':results},indent=2)+'\n',encoding='utf-8')
    observed=results['invalid transfer']['facts'].get('invalid_amount_http')
    status='ERROR' if observed is None else 'PASS' if observed in (400,422) else 'FAIL'
    results['API-04 exact status']={'status':status,'expected':[400,422],'actual':observed}
    args.out.write_text(json.dumps({'commit':rev,'seed':20261115,'cases':results},indent=2)+'\n',encoding='utf-8')
    suite=ET.Element('testsuite',name='Independent bank scenarios',tests=str(len(results)))
    for name,row in results.items():
        node=ET.SubElement(suite,'testcase',name=name,classname='mentor.bank')
        if row['status']!='PASS':
            tag='error' if row['status']=='ERROR' else 'failure'
            message=row.get('detail',f"Expected {row.get('expected')}, observed {row.get('actual')}")
            ET.SubElement(node,tag,message=message)
    for tag,attr in [('failure','failures'),('error','errors')]:
        suite.set(attr,str(len(suite.findall('.//'+tag))))
    ET.ElementTree(suite).write(args.out.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
    return int(any(r['status']!='PASS' for r in results.values()))


if __name__=='__main__':
    sys.exit(main())
