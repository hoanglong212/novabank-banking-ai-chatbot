"""Real SQLite / HTTP account lifecycle, including replay and migration boundaries."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException

from app.main import get_db
from .conftest import sign_in
from .test_ledger import report

PASSWORD = 'A long demo passphrase 2026!'
NEW_PASSWORD = 'A different passphrase 2026!'


def register(client, **changes):
    payload = dict(username='dana', name='Đặng An', email='dana@example.test', password=PASSWORD)
    payload.update(changes)
    response = client.post('/api/auth/register', json=payload)
    assert response.status_code == 202, response.text
    return response


def mail(kind, user='dana'):
    with get_db().connect() as conn:
        row = conn.execute('SELECT * FROM dev_outbox WHERE user_id=? AND kind=? ORDER BY rowid DESC LIMIT 1', (user, kind)).fetchone()
    assert row is not None
    return dict(row)


def token(kind, user='dana'):
    return parse_qs(urlsplit(mail(kind, user)['action_path']).fragment.split('?', 1)[1])['token'][0]


def verified(client):
    register(client)
    value = token('VERIFY_EMAIL')
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 200
    return sign_in(client, 'dana', PASSWORD)


def request_reset(client, user='dana', email='dana@example.test'):
    assert client.post('/api/auth/forgot-password', json={'email': email}).status_code == 202
    return token('RESET_PASSWORD', user)


def reset(client, value, password=NEW_PASSWORD):
    return client.post('/api/auth/reset-password', json={'token': value, 'password': password})


def test_register_verify_and_login_creates_one_zero_balance_account(client):
    result = register(client, username=' Dana ', email='Dana@Example.Test')
    assert all(word not in result.text for word in [PASSWORD, 'access_token', 'action_path'])
    assert client.post('/api/auth/login', json={'username': 'dana', 'password': PASSWORD}).status_code == 401
    value = token('VERIFY_EMAIL')
    with get_db().connect() as conn:
        row = conn.execute('SELECT * FROM users WHERE id=?', ('dana',)).fetchone()
        assert row['password_hash'] != PASSWORD and row['status'] == 'PENDING'
        assert conn.execute('SELECT COUNT(*) FROM accounts WHERE owner_id=?', ('dana',)).fetchone()[0] == 0
        stored = conn.execute('SELECT token_hash FROM identity_tokens WHERE user_id=?', ('dana',)).fetchone()[0]
        assert stored == hashlib.sha256(value.encode()).hexdigest() and stored != value
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 200
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 400
    user = sign_in(client, 'dana', PASSWORD)
    me = client.get('/api/me', headers=user).json()
    assert me['name'] == 'Đặng An' and me['role'] == 'customer'
    assert len(me['accounts']) == 1 and me['accounts'][0]['balance_vnd'] == 0
    assert me['transactions'] == []
    assert client.get('/api/transactions/TX-1001', headers=user).status_code == 404
    assert client.get('/api/admin/transactions', headers=user).status_code == 403
    assert report(get_db())['balanced']


def test_duplicates_do_not_overwrite_pending_identity_or_disclose_presence(client):
    first = register(client)
    value = token('VERIFY_EMAIL')
    duplicate = register(client, password=NEW_PASSWORD, name='Attacker', email='someone@example.test')
    email_duplicate = register(client, username='someone')
    assert first.json() == duplicate.json() == email_duplicate.json()
    assert token('VERIFY_EMAIL') == value
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 200
    assert client.post('/api/auth/login', json={'username': 'dana', 'password': NEW_PASSWORD}).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'dana', 'password': PASSWORD}).status_code == 202
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id IN ('dana','someone')").fetchone()[0] == 1


@pytest.mark.parametrize('change', [
    {'role': 'admin'}, {'balance_vnd': 1000000}, {'username': 'bad name'},
    {'username': 'a'}, {'email': 'bad@'}, {'email': 'a\nb@example.test'},
    {'name': ' '}, {'password': 'short-secret'}, {'password': 'x' * 129},
])
def test_invalid_registration_rejected_without_echoing_password(client, change):
    response = client.post('/api/auth/register', json={
        'username': 'dana', 'name': 'Dana', 'email': 'dana@example.test', 'password': PASSWORD, **change})
    assert response.status_code == 422
    assert PASSWORD not in response.text and 'short-secret' not in response.text


def test_resend_replaces_token_and_tokens_are_purpose_bound(client):
    register(client)
    old = token('VERIFY_EMAIL')
    response = client.post('/api/auth/resend-verification', json={'email': 'dana@example.test'})
    assert response.status_code == 202
    fresh = token('VERIFY_EMAIL')
    assert fresh != old
    assert client.post('/api/auth/verify-email', json={'token': old}).status_code == 400
    assert reset(client, fresh).status_code == 400
    assert client.post('/api/auth/verify-email', json={'token': fresh}).status_code == 200
    recovery = request_reset(client)
    assert client.post('/api/auth/verify-email', json={'token': recovery}).status_code == 400
    assert reset(client, recovery).status_code == 200


def test_tokens_expire_and_do_not_mutate_identity(client, monkeypatch):
    from app import identity
    register(client)
    value = token('VERIFY_EMAIL')
    deadline = mail('VERIFY_EMAIL')['expires_at']
    with monkeypatch.context() as clock:
        clock.setattr(identity, 'timestamp', lambda: deadline)
        assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 400
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 200
    recovery = request_reset(client)
    deadline = mail('RESET_PASSWORD')['expires_at']
    clock_now = identity.timestamp()
    assert deadline - clock_now in range(898, 901)
    monkeypatch.setattr(identity, 'timestamp', lambda: deadline)
    assert reset(client, recovery).status_code == 400
    assert client.post('/api/auth/login', json={'username': 'dana', 'password': PASSWORD}).status_code == 202


def test_reset_invalidates_all_old_sessions_and_survives_startup(client):
    old = verified(client)
    recovery = request_reset(client)
    result = reset(client, recovery)
    assert result.status_code == 200 and 'access_token' not in result.text
    assert reset(client, recovery).status_code == 400
    assert client.get('/api/me', headers=old).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'dana', 'password': PASSWORD}).status_code == 401
    fresh = sign_in(client, 'dana', NEW_PASSWORD)
    get_db().initialize()
    assert client.get('/api/me', headers=fresh).status_code == 200
    assert client.get('/api/me', headers=old).status_code == 401
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM accounts WHERE owner_id=?', ('dana',)).fetchone()[0] == 1
        audit = json.dumps([dict(r) for r in conn.execute('SELECT * FROM identity_audit')])
        assert PASSWORD not in audit and NEW_PASSWORD not in audit and recovery not in audit
    assert mail('RESET_PASSWORD')['action_path'] is None
    assert mail('PASSWORD_CHANGED')['action_path'] is None


def test_seed_password_reset_is_not_undone_by_migration(client, alice):
    value = request_reset(client, 'alice', 'alice@novabank.test')
    assert reset(client, value).status_code == 200
    get_db().initialize()
    assert client.get('/api/me', headers=alice).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'Alice@2026'}).status_code == 401
    assert sign_in(client, 'alice', NEW_PASSWORD)
    with get_db().connect() as conn:
        assert conn.execute("SELECT balance_vnd FROM accounts WHERE id='ACC-ALICE-001'").fetchone()[0] == 12_500_000
    assert report(get_db())['balanced']


def test_unknown_and_pending_recovery_have_same_public_response(client):
    register(client)
    known = client.post('/api/auth/forgot-password', json={'email': 'alice@novabank.test'})
    unknown = client.post('/api/auth/forgot-password', json={'email': 'missing@example.test'})
    pending = client.post('/api/auth/forgot-password', json={'email': 'dana@example.test'})
    assert known.status_code == unknown.status_code == pending.status_code == 202
    assert known.json() == unknown.json() == pending.json()
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE kind='RESET_PASSWORD'").fetchone()[0] == 1
    for path in ['/api/dev/outbox', '/api/auth/outbox', '/api/admin/outbox']:
        assert client.get(path).status_code == 404


def test_verification_and_reset_consume_once_under_concurrency(client):
    register(client)
    value = token('VERIFY_EMAIL')
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: client.post('/api/auth/verify-email', json={'token': value}).status_code, range(2)))
    assert sorted(codes) == [200, 400]
    recovery = request_reset(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: reset(client, recovery).status_code, range(2)))
    assert sorted(codes) == [200, 400]
    assert report(get_db())['balanced']


def test_storage_failure_rolls_back_verification_and_leaves_token_retryable(client):
    register(client)
    value = token('VERIFY_EMAIL')
    with get_db().connect() as conn:
        conn.execute("CREATE TRIGGER fail_new_mapping BEFORE INSERT ON ledger_accounts WHEN NEW.kind='CUSTOMER' BEGIN SELECT RAISE(ABORT,'test'); END")
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 503
    with get_db().connect() as conn:
        assert conn.execute("SELECT status FROM users WHERE id='dana'").fetchone()[0] == 'PENDING'
        assert conn.execute("SELECT COUNT(*) FROM accounts WHERE owner_id='dana'").fetchone()[0] == 0
        conn.execute('DROP TRIGGER fail_new_mapping')
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 200
    assert report(get_db())['balanced']


def test_recovery_delivery_and_request_limits_persist(client):
    for _ in range(8):
        assert client.post('/api/auth/forgot-password', json={'email': 'alice@novabank.test'}).status_code == 202
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE kind='RESET_PASSWORD'").fetchone()[0] == 5
    get_db().initialize()
    for _ in range(12):
        assert client.post('/api/auth/forgot-password', json={'email': 'missing@example.test'}).status_code == 202
    assert client.post('/api/auth/forgot-password', json={'email': 'missing@example.test'}).status_code == 429


def test_new_customer_can_receive_money_without_breaking_ledger(client, alice):
    from .test_banking_core import confirm
    who = verified(client)
    account = client.get('/api/me', headers=who).json()['accounts'][0]['id']
    draft = client.post('/api/transfers', headers=alice, json={'to_account': account, 'amount_vnd': 1000}).json()
    assert confirm(client, alice, draft, 'new-customer-payment').status_code == 200
    assert client.get('/api/me', headers=who).json()['accounts'][0]['balance_vnd'] == 1000
    assert client.get('/api/notifications', headers=who).json()['unread_count'] == 1
    assert report(get_db())['balanced']


def test_reset_failure_keeps_old_password_session_and_token_retryable(client):
    who = verified(client)
    recovery = request_reset(client)
    with get_db().connect() as conn:
        conn.execute("CREATE TRIGGER fail_reset_notice BEFORE INSERT ON dev_outbox WHEN NEW.kind='PASSWORD_CHANGED' BEGIN SELECT RAISE(ABORT,'test'); END")
    assert reset(client, recovery).status_code == 503
    assert client.get('/api/me', headers=who).status_code == 200
    assert sign_in(client, 'dana', PASSWORD)
    with get_db().connect() as conn:
        conn.execute('DROP TRIGGER fail_reset_notice')
    assert reset(client, recovery).status_code == 200
    assert client.get('/api/me', headers=who).status_code == 401


def test_repeated_reset_request_invalidates_previous_link(client):
    verified(client)
    old = request_reset(client)
    fresh = request_reset(client)
    assert old != fresh
    assert reset(client, old).status_code == 400
    assert reset(client, fresh).status_code == 200


def test_simultaneous_duplicate_registration_only_creates_one_identity(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: register(client), range(2)))
    assert responses[0].json() == responses[1].json()
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id='dana'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE user_id='dana'").fetchone()[0] == 1


@pytest.mark.parametrize('purpose', ['VERIFY_EMAIL', 'RESET_PASSWORD'])
def test_expiry_is_rechecked_after_waiting_for_database_write_lock(client, monkeypatch, purpose):
    from app import identity
    if purpose == 'VERIFY_EMAIL':
        register(client)
        value = token(purpose)
    else:
        verified(client)
        value = request_reset(client)
    deadline = mail(purpose)['expires_at']
    clock = [deadline - 1]
    monkeypatch.setattr(identity, 'timestamp', lambda: clock[0])
    original = identity.transaction

    @contextmanager
    def delayed_lock(db):
        with original(db) as conn:
            clock[0] = deadline  # Simulate the time elapsed while waiting for SQLite's write lock.
            yield conn

    monkeypatch.setattr(identity, 'transaction', delayed_lock)
    with pytest.raises(HTTPException) as failure:
        if purpose == 'VERIFY_EMAIL':
            identity.verify_email(get_db(), value)
        else:
            identity.reset_password(get_db(), value, NEW_PASSWORD)
    assert failure.value.status_code == 400
