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


@pytest.fixture()
def alice():
    return {'Authorization': 'Bearer demo-alice-token'}


@pytest.fixture()
def bob():
    return {'Authorization': 'Bearer demo-bob-token'}


def new_chat(client, headers):
    response = client.post('/api/conversations', headers=headers, json={'title': 'Testing'})
    assert response.status_code == 201, response.text
    return response.json()['id']
