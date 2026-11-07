from concurrent.futures import ThreadPoolExecutor
import json
import time
import jwt
import pytest
from app.main import get_db
from app import auth


def begin(client, username='alice', password='Alice@2026', **kwargs):
    response = client.post('/api/auth/login', json={'username': username, 'password': password}, **kwargs)
    assert response.status_code == 202, response.text
    assert 'access_token' not in response.text and 'refresh_token' not in response.text
    return response.json()


def email_code(challenge):
    from app.identity import digest
    with get_db().connect() as conn:
        row = conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1',
                           (digest(challenge['challenge_id']),)).fetchone()
    assert row and row[0]
    return row[0]


def verify(client, challenge, code=None):
    return client.post('/api/auth/mfa/verify', json={'challenge_id': challenge['challenge_id'], 'code': code or email_code(challenge)})


def signed(client, username='alice', password='Alice@2026', **kwargs):
    challenge = begin(client, username, password, **kwargs)
    response = verify(client, challenge)
    assert response.status_code == 200, response.text
    return response.json()


def headers(session):
    return {'Authorization': 'Bearer ' + session['access_token']}


def refresh(client, session):
    return client.post('/api/auth/refresh', json={'refresh_token': session['refresh_token']})


def test_password_login_requires_mfa_and_consumes_challenge_once(client):
    challenge = begin(client)
    assert challenge['method'] == 'email'
    assert client.get('/api/me', headers={'Authorization': 'Bearer ' + challenge['challenge_id']}).status_code == 401
    code = email_code(challenge)
    assert code not in json.dumps(challenge)
    response = verify(client, challenge, code)
    assert response.status_code == 200
    session = response.json()
    assert client.get('/api/me', headers=headers(session)).status_code == 200
    assert session['expires_in'] == 300 and session['session_id']
    assert verify(client, challenge, code).status_code == 400
    with get_db().connect() as conn:
        assert conn.execute('SELECT secret_text FROM dev_outbox WHERE kind=\'LOGIN_OTP\'').fetchone()[0] is None
        assert conn.execute('SELECT COUNT(*) FROM user_sessions').fetchone()[0] == 1


def test_persistent_lockout_for_15_minutes_and_success_resets_failures(client, monkeypatch):
    from app import session_security as security
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock)
    for _ in range(5):
        assert client.post('/api/auth/login', json={'username': 'ALICE', 'password': 'wrong'}).status_code == 401
    get_db().initialize()
    assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'Alice@2026'}).status_code == 429
    clock += 899
    assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'Alice@2026'}).status_code == 429
    clock += 1
    session = signed(client)
    assert client.get('/api/me', headers=headers(session)).status_code == 200
    assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'wrong'}).status_code == 401


def test_mfa_failure_budget_survives_resend_restart_and_new_challenge(client, monkeypatch):
    from app import session_security as security
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock)
    challenge = begin(client)
    old = email_code(challenge)
    wrong = '111111' if old != '111111' else '222222'
    for _ in range(3):
        assert verify(client, challenge, wrong).status_code == 400
    clock += 31
    assert client.post('/api/auth/mfa/email', json={'challenge_id': challenge['challenge_id']}).status_code == 202
    assert email_code(challenge) != old
    get_db().initialize()
    for _ in range(2):
        assert verify(client, challenge, old).status_code == 400
    assert verify(client, challenge, old).status_code in (400, 429)
    assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'Alice@2026'}).status_code == 429


def test_expired_mfa_and_wrong_purpose_have_no_session_effect(client, monkeypatch):
    from app import session_security as security
    challenge = begin(client)
    code = email_code(challenge)
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock + 120)
    assert verify(client, challenge, code).status_code == 400
    assert client.post('/api/auth/verify-email', json={'token': challenge['challenge_id']}).status_code == 400
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM user_sessions').fetchone()[0] == 0


def test_mfa_concurrent_consumption_creates_one_session(client):
    challenge = begin(client)
    code = email_code(challenge)
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda _: verify(client, challenge, code).status_code, range(2)))
    assert sorted(codes) == [200, 400]


def test_refresh_rotation_reuse_revokes_family_but_not_other_sessions(client):
    first, other = signed(client), signed(client)
    rotated = refresh(client, first)
    assert rotated.status_code == 200
    fresh = rotated.json()
    assert fresh['refresh_token'] != first['refresh_token'] and fresh['session_id'] == first['session_id']
    assert refresh(client, first).status_code == 401
    assert client.get('/api/me', headers=headers(fresh)).status_code == 401
    assert refresh(client, fresh).status_code == 401
    assert client.get('/api/me', headers=headers(other)).status_code == 200
    with get_db().connect() as conn:
        assert first['refresh_token'] not in json.dumps([dict(r) for r in conn.execute('SELECT * FROM refresh_tokens')])


def test_revoke_ownership_logout_and_legacy_tokens(client):
    first, second, bob = signed(client), signed(client), signed(client, 'bob', 'Bob@2026')
    rows = client.get('/api/auth/sessions', headers=headers(first)).json()['items']
    assert len(rows) == 2 and sum(r['current'] for r in rows) == 1
    assert client.delete('/api/auth/sessions/' + second['session_id'], headers=headers(bob)).status_code == 404
    assert client.delete('/api/auth/sessions/' + second['session_id'], headers=headers(first)).status_code == 200
    assert client.get('/api/me', headers=headers(second)).status_code == 401
    assert refresh(client, second).status_code == 401
    assert client.post('/api/auth/logout', headers=headers(first)).status_code == 200
    assert client.get('/api/me', headers=headers(first)).status_code == 401
    old = jwt.encode({'sub': 'alice', 'iss': auth.ISSUER, 'iat': int(time.time()), 'exp': int(time.time()) + 600, 'ver': 0}, auth.SECRET, algorithm='HS256')
    assert client.get('/api/me', headers={'Authorization': 'Bearer ' + old}).status_code == 401


def test_idle_timeout_ignores_polling_refresh_but_accepts_activity(client, monkeypatch):
    from app import session_security as security
    session = signed(client)
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock)
    clock += 240
    assert client.get('/api/notifications', headers=headers(session)).status_code == 200
    rotated = refresh(client, session).json()
    clock += 60
    assert client.get('/api/me', headers=headers(rotated)).status_code == 401
    assert refresh(client, rotated).status_code == 401
    active = signed(client)
    clock += 240
    assert client.post('/api/auth/activity', headers=headers(active)).status_code == 200
    clock += 100
    assert client.get('/api/me', headers=headers(active)).status_code == 200


def test_absolute_lifetime_cannot_be_extended_and_reset_revokes_refresh(client, monkeypatch):
    from app import session_security as security
    original_timestamp = security.timestamp
    session = signed(client)
    deadline = session['absolute_expires_at']
    with get_db().connect() as conn:
        conn.execute('UPDATE user_sessions SET last_active_at=?', (deadline - 1,))
    monkeypatch.setattr(security, 'timestamp', lambda: deadline)
    assert refresh(client, session).status_code == 401
    monkeypatch.setattr(security, 'timestamp', original_timestamp)
    session = signed(client)
    from .test_identity import request_reset, reset
    assert reset(client, request_reset(client, 'alice', 'alice@novabank.test')).status_code == 200
    assert refresh(client, session).status_code == 401


def test_login_history_owner_scope_and_new_device_notice(client):
    first = signed(client, headers={'User-Agent': 'Device One'})
    signed(client, headers={'User-Agent': 'Device Two'})
    bob = signed(client, 'bob', 'Bob@2026')
    history = client.get('/api/auth/login-history?limit=1', headers=headers(first)).json()
    assert history['total'] >= 2 and len(history['items']) == 1
    assert history['items'][0]['result'] == 'SUCCESS'
    own = client.get('/api/auth/login-history', headers=headers(bob)).json()
    assert all(r['user_id'] == 'bob' for r in own['items'])
    assert not any(k in json.dumps(history) for k in ['password_hash', 'refresh_token', 'otp_hash'])
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE user_id='alice' AND kind='NEW_DEVICE'").fetchone()[0] == 1


def test_totp_rfc_vectors():
    from app.auth_crypto import totp
    secret = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'
    for stamp, expected in [(59, '94287082'), (1111111109, '07081804'), (1111111111, '14050471'), (1234567890, '89005924'), (2000000000, '69279037'), (20000000000, '65353130')]:
        assert totp(secret, stamp // 30, digits=8) == expected


def test_totp_setup_login_replay_fallback_and_disable(client, monkeypatch):
    from app import session_security as security
    from app.auth_crypto import totp
    current = signed(client)
    auth_headers = headers(current)
    setup = client.post('/api/auth/mfa/setup', headers=auth_headers, json={'password': 'Alice@2026'})
    assert setup.status_code == 200, setup.text
    secret = setup.json()['secret']
    assert setup.json()['otpauth_uri'].startswith('otpauth://totp/')
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock)
    code = totp(secret, clock // 30)
    assert client.post('/api/auth/mfa/enable', headers=auth_headers, json={'code': code}).status_code == 200
    assert client.get('/api/auth/mfa', headers=auth_headers).json()['totp_enabled'] is True
    challenge = begin(client)
    assert challenge['method'] == 'totp'
    assert verify(client, challenge, code).status_code == 400
    clock += 30
    session = verify(client, challenge, totp(secret, clock // 30)).json()
    assert session['access_token']
    fallback = begin(client)
    assert client.post('/api/auth/mfa/email', json={'challenge_id': fallback['challenge_id']}).status_code == 202
    assert verify(client, fallback).status_code == 200
    disable = client.post('/api/auth/mfa/disable-request', headers=auth_headers, json={'password': 'Alice@2026'}).json()
    assert verify(client, disable).status_code == 400  # Wrong action, not a login challenge.
    result = client.post('/api/auth/mfa/disable', headers=auth_headers, json={'challenge_id': disable['challenge_id'], 'code': email_code(disable)})
    assert result.status_code == 200, result.text
    assert client.get('/api/me', headers=headers(session)).status_code == 401
    assert client.get('/api/auth/mfa', headers=auth_headers).json()['totp_enabled'] is False
    with get_db().connect() as conn:
        serialized = json.dumps([dict(r) for r in conn.execute('SELECT * FROM mfa_settings')])
        assert secret not in serialized


def test_trusted_device_skips_login_mfa_until_revoked_or_stale(client):
    from app.mfa import TRUSTED_DEVICE_SECONDS
    first = signed(client)
    device = first['device_token']
    login = lambda user='alice', pw='Alice@2026', token=device: client.post(
        '/api/auth/login', json={'username': user, 'password': pw, 'device_token': token}).json()
    session = login()
    assert session['access_token'] and client.get('/api/me', headers=headers(session)).status_code == 200
    assert login(pw='wrong').get('access_token') is None  # Password is still checked.
    assert login(user='bob', pw='Bob@2026').get('mfa_required')  # Token is bound to its user.
    with get_db().connect() as conn:
        conn.execute('UPDATE trusted_devices SET last_used_at=last_used_at-?', (TRUSTED_DEVICE_SECONDS + 1,))
    assert login().get('mfa_required')
    device = signed(client)['device_token']
    with get_db().connect() as conn:
        conn.execute('UPDATE users SET auth_version=auth_version+1 WHERE id=?', ('alice',))  # e.g. password change
    assert login(token=device).get('mfa_required')


def test_staff_never_get_trusted_device(client):
    assert 'device_token' not in signed(client, 'admin', 'Admin@2026')
