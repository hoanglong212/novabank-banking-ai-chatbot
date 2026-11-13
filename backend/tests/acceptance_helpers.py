"""Isolated acceptance fixtures migrated from the 2026-11-01 audit probes."""
from pathlib import Path
import csv
from datetime import date
import io
import json
import sys
import pytest

ROOT = next(path for path in Path(__file__).resolve().parents if (path / 'backend/app/main.py').is_file())
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT))
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
    from tests.conftest import TokenClient  # remembers B5 confirmation tokens
    with TokenClient(app) as result:
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
    response = client.post('/api/transfers/'+draft['id']+'/confirm', headers=who, json={'otp':transfer_code(draft)})
    assert response.status_code == 200
    return response.json()

def beneficiary(client, who, account='ACC-BOB-001', nickname='Family'):
    response=client.post('/api/customer/beneficiaries', headers=who, json={'account_id':account,'bank':'NovaBank','nickname':nickname})
    assert response.status_code==201
    return response.json()


from tests.conftest import transfer_code
