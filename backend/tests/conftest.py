import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('LLM_PROVIDER', 'mock')
    monkeypatch.setenv('GATEWAY_MODE', 'local')
    monkeypatch.setenv('JWT_SECRET', 'test-signing-secret-' * 4)
    monkeypatch.setenv('APP_ORIGINS', 'https://testserver')
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'true')
    monkeypatch.setenv('DEMO_ALICE_PASSWORD', 'Alice-Test-Password-42')
    monkeypatch.setenv('DEMO_BOB_PASSWORD', 'Bob-Test-Password-42')
    with TestClient(app, base_url='https://testserver') as c:
        yield c


@pytest.fixture()
def alice(client):
    return signed_headers(client, 'alice', 'Alice-Test-Password-42')


@pytest.fixture()
def bob(client):
    return signed_headers(client, 'bob', 'Bob-Test-Password-42')


def signed_headers(client, username, password):
    result = client.post('/api/auth/login', headers={'Origin':'https://testserver'},
                         json={'username':username,'password':password})
    assert result.status_code == 200, result.text
    headers = {'Cookie':'novabank_session='+client.cookies.get('novabank_session'),
               'X-CSRF-Token':result.json()['csrf_token'],'Origin':'https://testserver'}
    client.cookies.clear()
    return headers


def new_chat(client, headers):
    response = client.post('/api/conversations', headers=headers, json={'title': 'Testing'})
    assert response.status_code == 201, response.text
    return response.json()['id']
