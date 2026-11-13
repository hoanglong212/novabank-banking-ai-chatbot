import re
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


class TokenClient(TestClient):
    """TestClient that remembers each draft's confirmation token (B5) and sends it on confirm.

    Only when the test leaves confirm_token out: B5 tests pass it explicitly (a bad value, or None for missing).
    The token always comes from a real bank response, so every older test still exercises real verification.
    """
    CONFIRM = re.compile(r'^/api/transfers/([^/?]+)/confirm$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.confirm_tokens = {}

    def request(self, method, url, *args, **kwargs):
        match = self.CONFIRM.match(str(url)) if method.upper() == 'POST' else None
        body = kwargs.get('json')
        if match and isinstance(body, dict) and 'confirm_token' not in body:
            token = self.confirm_tokens.get(match.group(1))
            if token is None:  # e.g. a draft prepared by the assistant: fetch it as the same user, like the UI does
                fetched = super().request('GET', '/api/transfers/' + match.group(1), headers=kwargs.get('headers'))
                token = fetched.json().get('confirm_token') if fetched.status_code == 200 else None
            if token:
                kwargs['json'] = {**body, 'confirm_token': token}
        response = super().request(method, url, *args, **kwargs)
        try:
            data = response.json()
        except ValueError:
            return response
        if isinstance(data, dict) and data.get('confirm_token') and isinstance(data.get('id'), str):
            self.confirm_tokens[data['id']] = data['confirm_token']
        return response


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'test.sqlite3'))
    monkeypatch.setenv('LLM_PROVIDER', 'mock')
    monkeypatch.setenv('GATEWAY_MODE', 'local')
    monkeypatch.setenv('BANK_WORKER_ENABLED', 'false')
    monkeypatch.setenv('LEGACY_AGENT_TEST_MODE', 'true')
    with TokenClient(app) as c:
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
