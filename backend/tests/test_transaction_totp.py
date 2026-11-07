from app import session_security as security
from app.auth_crypto import totp
from tests.acceptance_helpers import *
from tests.test_identity import PASSWORD, verified


def enable_authenticator(client, who, password, monkeypatch):
    secret = client.post('/api/auth/mfa/setup', headers=who, json={'password': password}).json()['secret']
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock)
    assert client.post('/api/auth/mfa/enable', headers=who, json={'code': totp(secret, clock // 30)}).status_code == 200
    return secret, clock


def outbox_count(kind):
    with get_db().connect() as conn:
        return conn.execute('SELECT COUNT(*) FROM dev_outbox WHERE kind=?', (kind,)).fetchone()[0]


def test_transfer_uses_the_authenticator_code_once_and_mails_nothing(client, monkeypatch):
    who = login(client)
    secret, clock = enable_authenticator(client, who, 'Alice@2026', monkeypatch)
    mailed = outbox_count('TRANSFER_OTP')
    draft = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'totp'}).json()
    assert draft['otp_method'] == 'totp' and outbox_count('TRANSFER_OTP') == mailed
    # The enable step is already burned; the next step's code confirms.
    code = totp(secret, clock // 30 + 1)
    assert client.post(f"/api/transfers/{draft['id']}/confirm", headers=who, json={'otp': '000000'}).json()['detail'] == 'OTP_INVALID'
    assert client.post(f"/api/transfers/{draft['id']}/confirm", headers=who, json={'otp': code}).json()['status'] == 'COMPLETED'
    # The same code cannot approve a second payment.
    second = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'replay'}).json()
    assert client.post(f"/api/transfers/{second['id']}/confirm", headers=who, json={'otp': code}).json()['detail'] == 'OTP_INVALID'


def test_actions_use_the_authenticator_but_new_email_still_gets_a_code(client, monkeypatch):
    who = login(client)
    secret, clock = enable_authenticator(client, who, 'Alice@2026', monkeypatch)
    name = client.post('/api/customer/profile/change', headers=who, json={'field': 'name', 'value': 'Alice N', 'password': 'Alice@2026'}).json()
    assert name['method'] == 'totp'
    confirm = lambda code: client.post('/api/actions/confirm', headers={**who, 'Idempotency-Key': 'totp-' + code},
                                       json={'challenge_id': name['challenge_id'], 'code': code})
    assert confirm('000000').status_code == 400
    assert confirm(totp(secret, clock // 30 + 1)).status_code == 200
    email = client.post('/api/customer/profile/change', headers=who, json={'field': 'email', 'value': 'alice.totp@example.test', 'password': 'Alice@2026'}).json()
    assert email['method'] == 'email'


def test_new_accounts_must_set_a_pin_before_transacting(client):
    who = verified(client)
    assert client.get('/api/auth/mfa', headers=who).json()['setup_required'] is True
    blocked = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'x'})
    assert blocked.status_code == 403 and blocked.json()['detail'] == 'PIN_REQUIRED'
    assert client.post('/api/customer/profile/change', headers=who, json={'field': 'name', 'value': 'Dana', 'password': PASSWORD}).status_code == 403
    assert client.post('/api/auth/pin', headers=who, json={'password': PASSWORD, 'pin': '482916'}).status_code == 200
    assert client.get('/api/auth/mfa', headers=who).json()['setup_required'] is False
    # Seeded demo accounts are not forced; the app prompts them for a PIN at their first payment.
    assert client.get('/api/auth/mfa', headers=login(client)).json()['setup_required'] is False


def test_pin_confirms_payments_and_locks_after_five_misses(client):
    who = login(client)
    assert client.post('/api/auth/pin', headers=who, json={'password': 'wrong', 'pin': '482916'}).status_code == 400
    assert client.post('/api/auth/pin', headers=who, json={'password': 'Alice@2026', 'pin': '111111'}).status_code == 422
    assert client.post('/api/auth/pin', headers=who, json={'password': 'Alice@2026', 'pin': '123456'}).status_code == 422
    assert client.post('/api/auth/pin', headers=who, json={'password': 'Alice@2026', 'pin': '482916'}).status_code == 200
    mailed = outbox_count('TRANSFER_OTP')
    draft = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'pin'}).json()
    assert draft['otp_method'] == 'pin' and outbox_count('TRANSFER_OTP') == mailed
    confirm = lambda d, pin: client.post(f"/api/transfers/{d['id']}/confirm", headers=who, json={'otp': pin})
    assert confirm(draft, '000000').json()['detail'] == 'OTP_INVALID'
    assert confirm(draft, '482916').json()['status'] == 'COMPLETED'
    # Five wrong PINs across drafts lock the PIN, even the right one, for 15 minutes.
    for _ in range(4):
        d = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'x'}).json()
        confirm(d, '000000')
    d = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'x'}).json()
    assert confirm(d, '000000').json()['detail'] == 'PIN_LOCKED'


def test_pin_set_mid_payment_confirms_an_emailed_draft_but_never_an_email_change(client):
    who = login(client)
    draft = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'mid'}).json()
    assert draft['otp_method'] == 'email'
    email = client.post('/api/customer/profile/change', headers=who, json={'field': 'email', 'value': 'alice.pin@example.test', 'password': 'Alice@2026'}).json()
    client.post('/api/auth/pin', headers=who, json={'password': 'Alice@2026', 'pin': '482916'})
    assert client.post(f"/api/transfers/{draft['id']}/confirm", headers=who, json={'otp': '482916'}).json()['status'] == 'COMPLETED'
    assert client.post('/api/actions/confirm', headers={**who, 'Idempotency-Key': 'pin-email'},
                       json={'challenge_id': email['challenge_id'], 'code': '482916'}).status_code == 400
