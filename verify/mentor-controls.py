"""Defensive controls on seeded disposable data; only in-process TestClient and SQLite.

python verify/mentor-controls.py CLEAN_CHECKOUT EVIDENCE_JSON
"""
import argparse
import gc
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch


def main(root, output, tmp):
    os.chdir(root)
    assert not subprocess.check_output(['git','status','--porcelain']).strip()
    revision = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    os.environ.update(DB_PATH=str(tmp/'fresh.sqlite3'),ENV='demo',LLM_PROVIDER='mock',BANK_WORKER_ENABLED='false')
    subprocess.run([sys.executable,'scripts/seed_realistic.py','--seed','20261115','--output',os.environ['DB_PATH']],
                   check=True,stdout=subprocess.DEVNULL)
    sys.path[:0] = [str(root/'backend'),str(root)]
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from pydantic import ValidationError
    from app import mfa, posting, session_security
    from app.auth import authenticate
    from app.dependencies import get_db
    from app.identity import digest, transaction
    from app.database import now
    from app.main import app
    from app.routes_customer import Nickname
    db = get_db()
    results = {}

    def q(sql, args=()):
        with closing(db.connect()) as conn:
            return [tuple(row) for row in conn.execute(sql,args)]

    def balance(a):
        return q('SELECT balance_vnd FROM accounts WHERE id=?',(a,))[0][0]

    def response(r,expected):
        if r.status_code==429 or r.status_code>=500:
            raise RuntimeError(f'unexpected infrastructure status {r.status_code}')
        if r.status_code!=expected:
            raise AssertionError(f'expected {expected}, got {r.status_code}')
        return r.json()

    def observe(key,fn):
        try:
            results[key] = fn()
        except (AssertionError,KeyError) as exc:
            results[key] = {'result':'FAIL','reason':str(exc)}
        except RuntimeError as exc:
            results[key] = {'result':'ERROR','reason':str(exc)}
        except Exception as exc:
            results[key] = {'result':'ERROR','reason':type(exc).__name__}

    def ownership():
        before=balance('ACC-BOB-001')
        try:
            with transaction(db) as conn:
                posting.validate_accounts(conn,{'owner_id':'alice','from_account':'ACC-BOB-001'})
        except posting.TransferError as err:
            assert err.reason_code=='ACCOUNT_NOT_OWNED',err.reason_code
        else:
            raise AssertionError('Expected ownership denial from ledger validator')
        after=balance('ACC-BOB-001')
        assert before==after
        return dict(result='WEAK',unit='validate_accounts',reason='ACCOUNT_NOT_OWNED',
                    balance_before=before,balance_after=after,scope='Ledger unit; HTTP foreign-owner write not exercised')

    def schema():
        base={'nickname':'Mentor audit'}
        assert Nickname.model_validate(base).nickname==base['nickname']
        fields=['role','balance','owner_id']
        try:
            Nickname.model_validate({**base,**dict.fromkeys(fields,'unused')})
        except ValidationError as ex:
            assert {(e['loc'][0],e['type']) for e in ex.errors()}=={(f,'extra_forbidden') for f in fields}
        else:
            raise AssertionError('Unexpected allowed extra fields')
        return dict(result='WEAK',dto='Nickname',allowed_field='nickname',extra_forbidden=fields,
                    scope='Validator rejected all extras; no HTTP write was attempted, only one DTO sampled')

    def two_journals():
        a,b='ACC-ALICE-001','ACC-BOB-001'
        balances=[balance(a),balance(b)]
        n=balances[0]//2+1
        assert n>0
        gate=Barrier(2)
        def post(i):
            gate.wait(timeout=15)
            try:
                with transaction(db) as conn:
                    posting.post_journal(conn,'mentor-journal-'+str(i),[(a,-n),(b,n)],now())
                return 'posted'
            except posting.TransferError as ex:
                return ex.reason_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=sorted(pool.map(post,[1,2]))
        after=[balance(a),balance(b)]
        lines=q("SELECT COUNT(*), COALESCE(SUM(amount_vnd),0) FROM ledger_entries WHERE journal_id IN (?,?)",
                ('mentor-journal-1','mentor-journal-2'))[0]
        assert outcomes==['INSUFFICIENT_FUNDS','posted'] and tuple(lines)==(2,0)
        assert after==[balances[0]-n,balances[1]+n] and min(after)>=0
        return dict(result='WEAK',unit='BEGIN IMMEDIATE + post_journal, 2 local workers',outcomes=outcomes,
                    balances_before=balances,balances_after=after,single_journal_amount=n,ledger_rows=lines[0],
                    signed_journal_sum=lines[1],scope='No parallel HTTP transfer execution')

    def start(name,pw):
        r=response(client.post('/api/auth/login',json={'username':name,'password':pw}),202)
        assert r['mfa_required'] and 'access_token' not in r
        key=r['challenge_id']
        code=response(client.post('/api/dev/outbox/challenge',json={'challenge_id':key}),200)['code']
        return key,code

    def sessions(who):
        return q('SELECT COUNT(*) FROM user_sessions WHERE user_id=? AND revoked_at IS NULL',(who,))[0][0]

    def gate_check():
        before=sessions('alice')
        key,code=start('alice','Alice@2026')
        pending=sessions('alice')
        assert pending==before
        # A challenge is an opaque identifier, never a new session.
        try:
            authenticate('Bearer '+key)
        except HTTPException as err:
            assert err.status_code==401
        else:
            raise AssertionError('Session validator accepted a pending challenge')
        response(client.get('/api/me'),401)
        confirmed=response(client.post('/api/auth/mfa/verify',json={'challenge_id':key,'code':code}),200)
        auth_header={'Authorization':'Bearer '+confirmed['access_token']}
        assert response(client.get('/api/me',headers=auth_header),200)['id']=='alice'
        after=sessions('alice')
        assert after==before+1
        context.update(alice_headers=auth_header,completed_key=key,completed_code=code)
        return dict(result='WEAK',password_step=202,issued_session_before_mfa=False,
                    unit_pending_challenge_credential=401,unauthenticated_me=401,after_mfa_me=200,
                    sessions_before=before,sessions_pending=pending,sessions_after=after,
                    scope='Pending credential at authenticate() unit, ordinary /me HTTP before and after MFA')

    def otp_controls():
        def denied(key,code):
            try:
                mfa.complete(db,key,code)
            except HTTPException as ex:
                assert ex.status_code in (400,401,403,423),ex.status_code
                return ex.status_code
            raise AssertionError('Expected MFA challenge to be rejected')
        before=sessions('alice')
        replay=denied(context['completed_key'],context['completed_code'])
        assert before==sessions('alice')
        key,code=start('bob','Bob@2026')
        stamp=q('SELECT expires_at FROM mfa_challenges WHERE id=?',(digest(key),))[0][0]
        with patch.object(session_security,'timestamp',return_value=stamp):
            expired=denied(key,code)
        assert sessions('bob')==0
        # Test the boundary in one invocation, setting its two persisted counters directly.
        wrong=str((int(code)+1)%1000000).zfill(6)
        at=session_security.timestamp()
        with transaction(db) as conn:
            conn.execute('UPDATE mfa_challenges SET attempts=4 WHERE id=?',(digest(key),))
            conn.execute('INSERT OR REPLACE INTO login_lockouts(subject_hash,failures,window_start,locked_until) VALUES(?,4,?,0)',
                         (digest('bob'),at))
        rejected=denied(key,wrong)
        attempts,used=q('SELECT attempts,consumed_at IS NOT NULL FROM mfa_challenges WHERE id=?',(digest(key),))[0]
        failures,until=q('SELECT failures,locked_until FROM login_lockouts WHERE subject_hash=?',(digest('bob'),))[0]
        assert (attempts,used,failures)==(5,1,5) and until>at and sessions('bob')==0
        return dict(result='WEAK',unit='login email MFA',expired_status=expired,replay_status=replay,
                    wrong_status=rejected,failure_count=failures,consumed=bool(used),locked=until>at,
                    scope='Controlled expiry, one-time and lock threshold. Transfer OTP path and brute force not executed')

    def direct_auth():
        counts=q('SELECT COUNT(*) FROM agent_calls')[0][0]
        body=response(client.post('/api/agent/tools'),401)
        assert 'detail' in body and q('SELECT COUNT(*) FROM agent_calls')[0][0]==counts
        return dict(result='WEAK',missing_delegation=401,recorded_calls_before=counts,recorded_calls_after=counts,
                    scope='Normal missing-credential denial. No bypass scenario or delegated positive in this case')

    def ordinary_search():
        qtext="O'Brien"
        body=response(client.get('/api/customer/beneficiaries',params={'q':qtext},headers=context['alice_headers']),200)
        assert isinstance(body['items'],list)
        assert all(r['owner_id']=='alice' and any(qtext.casefold() in str(r.get(k,'')).casefold()
                   for k in ('nickname','holder_name','account_id')) for r in body['items'])
        return dict(result='WEAK',ordinary_name_search_status=200,returned=len(body['items']),
                    source='backend/app/customer_services.py:97; user ID and three LIKE values bound as parameters',
                    scope='Bound SQL and ordinary apostrophe-bearing name only; no SQL injection payload run')

    context={}
    with TestClient(app,raise_server_exceptions=False) as client:
        for key,fn in [('API-02',ownership),('API-03',schema),('API-05',direct_auth),('API-11',gate_check),
                       ('API-12',otp_controls),('API-09',ordinary_search),('API-08',two_journals)]:
            observe(key,fn)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'revision':revision,'fresh_seed':20261115,'results':results},
                                 indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['result'] for k,v in results.items()}))
    return int(any(r['result'] in ('FAIL','ERROR') for r in results.values()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with TemporaryDirectory(prefix='mentor-controls-') as d:
        code=main(args.checkout.resolve(),args.output.resolve(),Path(d))
        gc.collect()
    sys.exit(code)
