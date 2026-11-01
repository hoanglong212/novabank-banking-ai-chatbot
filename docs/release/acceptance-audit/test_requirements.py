"""Remaining historical audit probes. Red regressions now live in backend/tests/test_<CASE>.py.

See ../acceptance-fixes/REPORT_VI.md for the subsequent fixes and ratified expectations.
"""
from pathlib import Path
import csv
from datetime import date
import io
import json
import sys
import pytest

ROOT = next(path for path in Path(__file__).resolve().parents if (path / 'backend/app/main.py').is_file())
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi.testclient import TestClient
from app.main import app, get_db
from app.identity import digest
from app.ledger import reconcile

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'acceptance.sqlite3'))
    monkeypatch.setenv('LLM_PROVIDER', 'mock')
    monkeypatch.setenv('BANK_WORKER_ENABLED', 'false')
    monkeypatch.setenv('LEGACY_AGENT_TEST_MODE', 'false')
    with TestClient(app) as result:
        yield result
        assert reconcile(get_db())['balanced']

def login(client, user='alice'):
    response = client.post('/api/auth/login', json={'username': user, 'password': user.capitalize()+'@2026'})
    assert response.status_code == 202
    challenge = response.json()['challenge_id']
    with get_db().connect() as conn:
        code = conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=?', (digest(challenge),)).fetchone()[0]
    response = client.post('/api/auth/mfa/verify', json={'challenge_id': challenge, 'code': code})
    assert response.status_code == 200
    return {'Authorization': 'Bearer '+response.json()['access_token']}

def pay(client, who, amount=2000):
    response = client.post('/api/transfers', headers=who, json={'to_account':'ACC-BOB-001','amount_vnd':amount,'content':'acceptance probe'})
    assert response.status_code == 201
    draft = response.json()
    response = client.post('/api/transfers/'+draft['id']+'/confirm', headers=who, json={'otp':draft['demo_otp']})
    assert response.status_code == 200
    return response.json()

def beneficiary(client, who, account='ACC-BOB-001', nickname='Family'):
    response=client.post('/api/customer/beneficiaries', headers=who, json={'account_id':account,'bank':'NovaBank','nickname':nickname})
    assert response.status_code==201
    return response.json()











def test_AUTH_13_no_outbox_http_routes(client):
    assert not any('outbox' in path.lower() for path in app.openapi()['paths'])
    who=login(client)
    assert client.get('/api/dev-outbox',headers=who).status_code==404

def test_TXN_03_boundary_queries(client):
    who=login(client)
    assert client.get('/api/transactions?offset=999999',headers=who).json()['items']==[]
    assert client.get('/api/transactions?limit=999999',headers=who).status_code==422
    response=client.get('/api/transactions?from_date=2026-11-30&to_date=2026-11-01',headers=who)
    assert response.status_code in (400,422), f'Reversed dates returned {response.status_code}'

def test_SEC_05_literal_sql_search(client):
    who=login(client)
    response=client.get('/api/transactions',headers=who,params={'q':"%' OR 1=1;--"})
    assert response.status_code==200
    assert response.json()['items']==[]

def test_LED_07_scheduled_mismatch_alert(client):
    from app.workers import maintenance
    db=get_db()
    with db.connect() as conn:
        conn.execute("UPDATE accounts SET balance_vnd=balance_vnd+1 WHERE id='ACC-ALICE-001'")
        conn.execute('DELETE FROM reconciliation_runs')
    maintenance(db)
    with db.connect() as conn:
        count=conn.execute("SELECT COUNT(*) FROM service_notifications WHERE owner_id='admin' AND kind='RECONCILIATION'").fetchone()[0]
        conn.execute("UPDATE accounts SET balance_vnd=balance_vnd-1 WHERE id='ACC-ALICE-001'")
    assert count==1

@pytest.mark.parametrize('amount,term',[(100_000_000,3),(100_000,5)])
def test_SAV_02_invalid_savings_never_creates_deposit(client,amount,term):
    who=login(client)
    response=client.post('/api/products/actions',headers=who,json={'kind':'OPEN_SAVINGS','account_id':'ACC-ALICE-001','amount_vnd':amount,'term_months':term})
    assert response.status_code in (400,409,422)
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM savings WHERE owner_id='alice'").fetchone()[0]==0

def test_SEC_08_internal_error_hides_exception_detail(client):
    who=login(client)
    def broken(): raise RuntimeError('SELECT * FROM private_table at C:/private/secret.py')
    app.dependency_overrides[get_db]=broken
    try:
        with TestClient(app,raise_server_exceptions=False) as other:
            response=other.get('/api/customer/profile',headers=who)
        assert response.status_code==500
        assert not any(word in response.text for word in ('SELECT','private_table','secret.py','Traceback'))
    finally:
        app.dependency_overrides.pop(get_db,None)

def test_AUTH_16_seed_and_new_password_hash_iterations(client):
    from app.identity import hash_password
    assert login(client)
    assert hash_password('a sufficiently long test password').split('$')[1]=='600000'
    with get_db().connect() as conn:
        assert conn.execute("SELECT password_hash FROM users WHERE id='alice'").fetchone()[0].split('$')[1]=='310000'

def test_PI_03_reset_preserves_full_logical_database_hash(tmp_path,monkeypatch):
    import hashlib
    sys.path.insert(0,str(ROOT))
    from research import sandbox,scenarios
    monkeypatch.setattr(sandbox,'ROOT',tmp_path)
    lab=sandbox.Sandbox(tmp_path/'.local/research/acceptance/sandbox')
    def fingerprint():
        with lab.db.connect() as conn:
            return hashlib.sha256('\n'.join(conn.iterdump()).encode()).hexdigest()
    before=fingerprint()
    lab.source(scenarios.attacks()[0])
    assert fingerprint()!=before
    lab.reset(); assert fingerprint()==before
    lab.reset(); assert fingerprint()==before

