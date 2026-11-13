"""R1 reproduction: anonymous account takeover through the demo outbox.

See docs/release/week7-evidence/OUTBOX_TAKEOVER.md. Every request below is sent without an
Authorization header except where the attacker uses the session it has just stolen.
"""
import pytest
from tests.conftest import sign_in

NEW_PASSWORD = 'Attacker#2026-takeover'
PIN = '135790'


def newest_mail(client):
    item = client.get('/api/dev/outbox').json()['items'][0]
    return client.get('/api/dev/outbox/' + item['id']).json()


# strict: if the takeover ever succeeds again, this XPASS fails the suite.
@pytest.mark.xfail(strict=True, reason='R1 fixed: the outbox no longer serves other users mail or links anonymously')
def test_anonymous_outbox_takeover_chain(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    # 1. Guessable address: demo users are seeded as <username>@novabank.test.
    assert client.post('/api/auth/forgot-password', json={'email': 'alice@novabank.test'}).status_code == 202
    # 2. Read Alice's reset link from the shared inbox.
    token = newest_mail(client)['action_url'].split('token=')[1]
    # 3. Set a new password.
    assert client.post('/api/auth/reset-password', json={'token': token, 'password': NEW_PASSWORD}).status_code == 200
    # 4. Sign in and read Alice's sign-in code from the same inbox.
    challenge = client.post('/api/auth/login', json={'username': 'alice', 'password': NEW_PASSWORD}).json()['challenge_id']
    login = client.post('/api/auth/mfa/verify', json={'challenge_id': challenge, 'code': newest_mail(client)['code']})
    assert login.status_code == 200
    stolen = {'Authorization': 'Bearer ' + login.json()['access_token']}
    # 5. The attacker knows the password now, so it can create the transaction PIN and move money.
    assert client.post('/api/auth/pin', headers=stolen, json={'password': NEW_PASSWORD, 'pin': PIN}).status_code == 200
    draft = client.post('/api/transfers', headers=stolen, json={'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 5_000_000}).json()
    done = client.post(f'/api/transfers/{draft["id"]}/confirm', headers={**stolen, 'Idempotency-Key': 'r1-repro'}, json={'otp': PIN})
    assert done.status_code == 200 and done.json()['status'] == 'COMPLETED', done.text


def login_challenge(client, user='alice', password='Alice@2026'):
    response = client.post('/api/auth/login', json={'username': user, 'password': password})
    assert response.status_code == 202, response.text
    return response.json()['challenge_id']


def test_outbox_requires_sign_in_and_lists_only_own_mail(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    alice, bob = sign_in(client, 'alice', 'Alice@2026'), sign_in(client, 'bob', 'Bob@2026')
    assert client.get('/api/dev/outbox').status_code == 401
    bob_mail = client.get('/api/dev/outbox', headers=bob).json()['items']
    alice_mail = client.get('/api/dev/outbox', headers=alice).json()['items']
    assert bob_mail and alice_mail and not {m['id'] for m in bob_mail} & {m['id'] for m in alice_mail}
    assert client.get('/api/dev/outbox/' + bob_mail[0]['id']).status_code == 401
    assert client.get('/api/dev/outbox/' + bob_mail[0]['id'], headers=alice).status_code == 404
    assert client.get('/api/dev/outbox/' + bob_mail[0]['id'], headers=bob).status_code == 200


def test_sign_in_code_is_readable_only_with_its_challenge(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    alice, bob = login_challenge(client), login_challenge(client, 'bob', 'Bob@2026')
    mail = client.post('/api/dev/outbox/challenge', json={'challenge_id': alice})
    assert mail.status_code == 200 and mail.json()['kind'] == 'LOGIN_OTP' and len(mail.json()['code']) == 6
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': bob}).json()['code'] != mail.json()['code']
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': 'x' * 43}).status_code == 404
    assert client.post('/api/auth/mfa/verify', json={'challenge_id': alice, 'code': mail.json()['code']}).status_code == 200
    # Consumed: the code is scrubbed, and a challenge never unlocks a reset link.
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': alice}).json()['code'] is None


def test_reset_links_are_never_served_to_anonymous_clients(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    assert client.post('/api/auth/forgot-password', json={'email': 'alice@novabank.test'}).status_code == 202
    from app.dependencies import get_db
    with get_db().connect() as conn:
        mail_id = conn.execute("SELECT id FROM dev_outbox WHERE kind='RESET_PASSWORD'").fetchone()[0]
    assert client.get('/api/dev/outbox/' + mail_id).status_code == 401
    bob = sign_in(client, 'bob', 'Bob@2026')
    assert client.get('/api/dev/outbox/' + mail_id, headers=bob).status_code == 404


@pytest.mark.parametrize('environment', ['', 'production'])
def test_outbox_is_absent_outside_demo(client, monkeypatch, environment):
    monkeypatch.setenv('ENV', environment)
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': login_challenge(client)}).status_code == 404
    assert client.get('/api/dev/outbox').status_code == 404


def test_challenge_lookups_are_rate_limited_per_address(client, monkeypatch):
    from app.api.routes import dev
    monkeypatch.setenv('ENV', 'demo')
    monkeypatch.setattr(dev, 'CHALLENGE_POLLS', 3)
    challenge = login_challenge(client)
    statuses = [client.post('/api/dev/outbox/challenge', json={'challenge_id': challenge}).status_code for _ in range(4)]
    assert statuses == [200, 200, 200, 429]
    # Guessing other challenges spends the same budget.
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': 'x' * 43}).status_code == 429
