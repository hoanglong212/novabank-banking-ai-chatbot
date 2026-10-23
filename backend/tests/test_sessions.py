import time
import jwt
from fastapi.testclient import TestClient
from app.main import app

ORIGIN = 'https://testserver'


def login(c, username='alice', password='Alice-Test-Password-42'):
    return c.post('/api/auth/login', headers={'Origin':ORIGIN}, json={'username':username,'password':password})


def test_login_cookie_reload_logout(client, monkeypatch):
    monkeypatch.setenv('APP_ORIGINS', ORIGIN)
    monkeypatch.setenv('JWT_SECRET', 'test-signing-secret-' * 4)
    monkeypatch.setenv('DEMO_ALICE_PASSWORD', 'Alice-Test-Password-42')
    from app.sessions import initialize_auth
    from app.main import get_db
    initialize_auth(get_db())
    with TestClient(app, base_url=ORIGIN) as c:
        result = login(c)
        assert result.status_code == 200
        cookie = result.headers['set-cookie']
        assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=lax' in cookie
        assert 'token' not in result.json()
        csrf = result.json()['csrf_token']
        token = c.cookies.get('novabank_session')
        assert c.get('/api/auth/session').json()['user']['id'] == 'alice'
        assert c.post('/api/conversations', json={}).status_code == 403
        assert c.post('/api/conversations', headers={'Origin':'https://evil.example','X-CSRF-Token':csrf}, json={}).status_code == 403
        assert c.post('/api/conversations', headers={'Origin':ORIGIN,'X-CSRF-Token':csrf}, json={}).status_code == 201
        with TestClient(app, base_url=ORIGIN) as reloaded:
            reloaded.cookies.set('novabank_session', token)
            assert reloaded.get('/api/auth/session').status_code == 200
        assert c.post('/api/auth/logout', headers={'Origin':ORIGIN,'X-CSRF-Token':csrf}).status_code == 200
        c.cookies.set('novabank_session', token)
        assert c.get('/api/auth/session').status_code == 401


def test_forged_expired_and_demo_tokens_rejected(client, monkeypatch):
    monkeypatch.setenv('APP_ORIGINS', ORIGIN)
    monkeypatch.setenv('JWT_SECRET', 'test-signing-secret-' * 4)
    monkeypatch.setenv('DEMO_ALICE_PASSWORD', 'Alice-Test-Password-42')
    from app.sessions import initialize_auth
    from app.main import get_db
    initialize_auth(get_db())
    with TestClient(app, base_url=ORIGIN) as c:
        assert login(c).status_code == 200
        token = c.cookies.get('novabank_session')
        claims = jwt.decode(token, options={'verify_signature':False})
        for key, value in [('sub','bob'), ('exp',int(time.time())-10), ('aud','wrong')]:
            changed = {**claims,key:value}
            secret = 'wrong-key-'*8 if key == 'sub' else 'test-signing-secret-'*4
            c.cookies.clear()
            c.cookies.set('novabank_session', jwt.encode(changed,secret,algorithm='HS256'))
            assert c.get('/api/conversations').status_code == 401
        c.cookies.clear()
        assert c.get('/api/conversations',headers={'Authorization':'Bearer demo-alice-token'}).status_code == 401
        assert c.get('/api/demo/users').status_code == 404


def test_login_rate_limit_and_origin(client, monkeypatch):
    monkeypatch.setenv('APP_ORIGINS', ORIGIN)
    monkeypatch.setenv('JWT_SECRET', 'test-signing-secret-'*4)
    from app.sessions import initialize_auth
    from app.main import get_db
    initialize_auth(get_db())
    with TestClient(app,base_url=ORIGIN) as c:
        assert c.post('/api/auth/login', json={'username':'nobody','password':'wrong'}).status_code == 403
        for _ in range(5):
            assert login(c,'nobody','wrong').status_code == 401
        assert login(c,'nobody','wrong').status_code == 429
