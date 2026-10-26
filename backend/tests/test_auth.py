"""JWT login boundary."""
import time
import jwt
from app import auth


def test_login_and_me_only_returns_own_data(client, alice):
    me = client.get('/api/me', headers=alice).json()
    assert me['name'] == 'Alice' and [a['id'] for a in me['accounts']] == ['ACC-ALICE-001']
    assert {t['id'] for t in me['transactions']} == {'TX-1001', 'TX-1002', 'TX-1003', 'TX-1004'}


def test_wrong_password_and_unknown_user_look_the_same(client):
    for username in ('alice', 'nobody'):
        response = client.post('/api/auth/login', json={'username': username, 'password': 'wrong'})
        assert (response.status_code, response.json()['detail']) == (401, 'Invalid username or password')


def test_lockout_after_repeated_failures(client):
    codes = [client.post('/api/auth/login', json={'username': 'mallory', 'password': 'x'}).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_rejects_expired_forged_and_unsigned_tokens(client):
    now = int(time.time())
    claims = {'sub': 'alice', 'iss': auth.ISSUER, 'iat': now - 7200, 'exp': now - 3600}
    expired = jwt.encode(claims, auth.SECRET, algorithm='HS256')
    forged = jwt.encode({**claims, 'exp': now + 3600}, 'an-attacker-guess-that-is-long-enough-for-hs256', algorithm='HS256')
    unsigned = jwt.encode({**claims, 'exp': now + 3600}, None, algorithm='none')
    for token in (expired, forged, unsigned):
        assert client.get('/api/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_old_demo_token_endpoint_is_gone(client):
    assert client.get('/api/demo/users').status_code == 404
    assert client.get('/api/me', headers={'Authorization': 'Bearer demo-alice-token'}).status_code == 401
