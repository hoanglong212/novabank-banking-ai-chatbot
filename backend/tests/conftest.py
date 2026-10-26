import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('LLM_PROVIDER', 'mock')
    monkeypatch.setenv('GATEWAY_MODE', 'local')
    with TestClient(app) as c:
        yield c


def sign_in(client, username, password):
    response = client.post('/api/auth/login', json={'username': username, 'password': password})
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
