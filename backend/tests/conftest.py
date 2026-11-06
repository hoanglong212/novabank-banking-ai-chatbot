import pytest
from fastapi.testclient import TestClient
from app.main import app


def transfer_code(draft):
    """Test-only simulated email reader; cache to test replays after consumption."""
    if '_test_otp' not in draft:
        from app.dependencies import get_db
        with get_db().connect() as conn:
            row = conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1',
                               ('transfer:' + draft['id'],)).fetchone()
        draft['_test_otp'] = row[0] if row else draft.get('demo_otp')
    return draft['_test_otp']


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('LLM_PROVIDER', 'mock')
    monkeypatch.setenv('GATEWAY_MODE', 'local')
    monkeypatch.setenv('BANK_WORKER_ENABLED', 'false')
    monkeypatch.setenv('LEGACY_AGENT_TEST_MODE', 'true')
    with TestClient(app) as c:
        yield c


def sign_in(client, username, password):
    response = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 202, response.text
    # Complete real local email MFA; never install a test-only HTTP endpoint or bypass.
    from app.main import get_db
    from app.identity import digest
    challenge = response.json()['challenge_id']
    with get_db().connect() as conn:
        code = conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1',
                            (digest(challenge),)).fetchone()[0]
    response = client.post('/api/auth/mfa/verify', json={'challenge_id': challenge, 'code': code})
    assert response.status_code == 200, response.text
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


@pytest.fixture()
def alice(client):
    return sign_in(client, 'alice', 'Alice@2026')


@pytest.fixture()
def bob(client):
    return sign_in(client, 'bob', 'Bob@2026')


def new_chat(client, headers):
    response = client.post('/api/conversations', headers=headers, json={'title': 'Testing'})
    assert response.status_code == 201, response.text
    return response.json()['id']
