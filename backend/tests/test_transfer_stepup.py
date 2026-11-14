import asyncio
from dataclasses import replace
import json
import pytest
from app import auth, session_security as security, transfers
from app.auth_crypto import totp
from app.database import now
from app.schemas import TransferArgs
from tests.acceptance_helpers import client, login, get_db


@pytest.fixture(autouse=True)
def stepup_schema(client):
    from app import transfer_stepup
    with get_db().connect() as conn:
        transfer_stepup.initialize(conn, now())
        conn.execute("DELETE FROM verified_payees WHERE origin='fixture_known'")


def draft(who, account='ACC-BOB-001'):
    user = auth.authenticate(who['Authorization'])
    created = asyncio.run(transfers.prepare(get_db(), user, TransferArgs(to_account=account, amount_vnd=10000, content='Step-up test').model_dump(exclude_none=True)))
    with get_db().connect() as conn:
        return user, transfers._own_transfer(conn, created['id'], user)


def enable(client, who, monkeypatch):
    clock = security.timestamp()
    monkeypatch.setattr(security, 'timestamp', lambda: clock)
    result = client.post('/api/auth/mfa/setup', headers=who, json={'password': 'Alice@2026'})
    assert result.status_code == 200
    secret = result.json()['secret']
    assert client.post('/api/auth/mfa/enable', headers=who, json={'code': totp(secret, clock // 30 - 1)}).status_code == 200
    return secret, clock


def test_new_recipient_requires_enrollment_and_saved_beneficiary_is_not_a_bypass(client):
    from app import transfer_stepup
    who = login(client)
    user, transfer = draft(who)
    client.post('/api/customer/beneficiaries', headers=who, json={'account_id': 'ACC-BOB-001', 'bank': 'NovaBank', 'nickname': 'New saved person'}).raise_for_status()
    with get_db().connect() as conn:
        state = transfer_stepup.status(conn, user, transfer)
        assert state['required'] is True and state['enrollment_required'] is True
        with pytest.raises(Exception, match='AUTHENTICATOR_ENROLLMENT_REQUIRED'):
            transfer_stepup.require_stepup(conn, user, transfer)
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE kind='TRANSFER_OTP'").fetchone()[0] == 0
    assert client.get('/api/transfers/' + transfer['id'] + '/step-up', headers=who).json()['enrollment_required'] is True


def test_genuine_totp_is_bound_to_exact_draft_and_does_not_replace_final_otp(client, monkeypatch):
    from app import transfer_stepup
    who = login(client)
    secret, clock = enable(client, who, monkeypatch)
    user, transfer = draft(who)
    url = '/api/transfers/' + transfer['id'] + '/step-up'
    code = totp(secret, clock // 30)
    verified = client.post(url, headers=who, json={'code': code})
    assert verified.status_code == 200, verified.text
    assert verified.json()['verified'] is True and verified.json()['confirmation_method'] == 'email'
    assert client.post(url, headers=who, json={'code': code}).status_code == 400
    with get_db().connect() as conn:
        transfer_stepup.require_stepup(conn, user, transfer)
        assert transfer_stepup.email_confirmation_required(conn, user, transfer) is True
        assert conn.execute("SELECT COUNT(*) FROM dev_outbox WHERE kind='TRANSFER_OTP'").fetchone()[0] == 0
        assert conn.execute('SELECT balance_vnd FROM accounts WHERE id=?', ('ACC-ALICE-001',)).fetchone()[0] == 12500000
        for field, value in [('to_account', 'ACC-CHARLIE-001'), ('amount_vnd', 20000), ('fee_vnd', 999)]:
            with pytest.raises(Exception, match='STEP_UP_REQUIRED'):
                transfer_stepup.require_stepup(conn, user, {**transfer, field: value})
        stored = json.dumps([dict(r) for r in conn.execute('SELECT * FROM transfer_stepups')])
        assert code not in stored and secret not in stored
    _, second = draft(who)
    assert client.post('/api/transfers/' + second['id'] + '/step-up', headers=who, json={'code': code}).status_code == 400


def test_proof_expires_and_is_not_valid_for_another_session(client, monkeypatch):
    from app import transfer_stepup, sessions
    who = login(client)
    secret, clock = enable(client, who, monkeypatch)
    user, transfer = draft(who)
    assert client.post('/api/transfers/' + transfer['id'] + '/step-up', headers=who, json={'code': totp(secret, clock // 30)}).status_code == 200
    with get_db().connect() as conn:
        other = sessions.create(conn, user, '127.0.0.1', 'another-browser', 'totp', clock)
        other_user = replace(user, session_id=other['session_id'])
        with pytest.raises(Exception, match='STEP_UP_REQUIRED'):
            transfer_stepup.require_stepup(conn, other_user, transfer)
    monkeypatch.setattr(security, 'timestamp', lambda: clock + 121)
    with get_db().connect() as conn:
        with pytest.raises(Exception, match='STEP_UP_REQUIRED'):
            transfer_stepup.require_stepup(conn, user, transfer)


def test_wrong_owner_and_agent_token_cannot_verify_and_attempts_are_bounded(client, monkeypatch):
    who, bob = login(client), login(client, 'bob')
    secret, clock = enable(client, who, monkeypatch)
    _, transfer = draft(who)
    url = '/api/transfers/' + transfer['id'] + '/step-up'
    assert client.get(url, headers=bob).status_code == 404
    assert client.post(url, headers=bob, json={'code': totp(secret, clock // 30)}).status_code == 404
    assert client.get(url).status_code == 401
    from tests.test_AI_12 import run_for
    _, _, delegated = run_for(client, who)
    assert client.get(url, headers=delegated).status_code == 401
    assert client.post(url, headers=delegated, json={'code': totp(secret, clock // 30)}).status_code == 401
    correct = totp(secret, clock // 30)
    wrong = '000000' if correct != '000000' else '999999'
    for _ in range(5):
        assert client.post(url, headers=who, json={'code': wrong}).status_code in (400, 429)
    assert client.post(url, headers=who, json={'code': correct}).status_code == 429


def test_pending_payment_never_grants_trust_and_changing_authenticator_invalidates_proof(client, monkeypatch):
    from app import transfer_stepup
    from app.auth_crypto import encrypt_secret, new_totp_secret
    who = login(client)
    secret, clock = enable(client, who, monkeypatch)
    user, transfer = draft(who)
    assert client.post('/api/transfers/' + transfer['id'] + '/step-up', headers=who, json={'code': totp(secret, clock // 30)}).status_code == 200
    with get_db().connect() as conn:
        assert transfer_stepup.remember_completed(conn, transfer['id']) is False
        assert conn.execute('SELECT COUNT(*) FROM verified_payees').fetchone()[0] == 0
        conn.execute('UPDATE mfa_settings SET secret_encrypted=? WHERE user_id=?', (encrypt_secret(get_db(), new_totp_secret()), user.id))
        with pytest.raises(Exception, match='STEP_UP_REQUIRED'):
            transfer_stepup.require_stepup(conn, user, transfer)


def test_known_settled_recipient_preserves_existing_factors(client):
    from app import transfer_stepup
    from tests.stepup_helpers import mark_known
    who = login(client)
    user, transfer = draft(who)
    # Explicit fixed-fixture metadata, not an automatic TokenClient bypass.
    with get_db().connect() as conn:
        before = conn.execute('SELECT COUNT(*) FROM transfers').fetchone()[0]
        mark_known(conn, user.id, transfer['to_account'])
        state = transfer_stepup.status(conn, user, transfer)
        assert state['required'] is False and state['enrollment_required'] is False
        transfer_stepup.require_stepup(conn, user, transfer)
        assert transfer_stepup.email_confirmation_required(conn, user, transfer) is False
        assert conn.execute('SELECT COUNT(*) FROM transfers').fetchone()[0] == before
