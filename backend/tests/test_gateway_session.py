"""R3: gateway OFF is a time-boxed measurement session for named users, never a global switch."""
import json
import pytest
from tests.acceptance_helpers import client, login, get_db
from tests.test_agent_gateway import call, switch
from tests.test_week7 import grant_for


def gateway_of(client, who):
    _, _, token = grant_for(client, who, 'What is my balance?')
    return client.get('/api/agent/context', headers=token).json()['gateway'], token


def test_off_applies_only_to_the_named_users(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    admin, alice, bob = login(client, 'admin'), login(client), login(client, 'bob')
    assert switch(client, admin, False, users=['alice']).json() == {'gateway': 'off'}
    alice_gateway, _ = gateway_of(client, alice)
    bob_gateway, bob_token = gateway_of(client, bob)
    assert (alice_gateway, bob_gateway) == ('off', 'on')
    # Bob is fully protected while Alice is being measured.
    assert call(client, bob_token, 'list_customers', {})['reason'] == 'ROLE_NOT_PERMITTED'
    status = client.get('/api/admin/agent-gateway', headers=admin).json()
    assert status['gateway'] == 'off' and status['session']['users'] == ['alice']


def test_session_expires_back_to_on(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    admin, alice = login(client, 'admin'), login(client)
    switch(client, admin, False, users=['alice'])
    with get_db().connect() as conn:
        value = json.loads(conn.execute("SELECT value_json FROM bank_settings WHERE key='agent_gateway'").fetchone()[0])
        conn.execute("UPDATE bank_settings SET value_json=? WHERE key='agent_gateway'", (json.dumps({**value, 'expires_at': 1}),))
    assert gateway_of(client, alice)[0] == 'on'
    status = client.get('/api/admin/agent-gateway', headers=admin).json()
    assert (status['gateway'], status['session']) == ('on', None)


def test_switching_on_closes_the_session(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    admin, alice = login(client, 'admin'), login(client)
    switch(client, admin, False, users=['alice'])
    switch(client, admin, True)
    assert gateway_of(client, alice)[0] == 'on'


@pytest.mark.parametrize('payload', [{'enabled': False}, {'enabled': False, 'users': []}, {'enabled': False, 'users': ['nobody']},
                                     {'enabled': False, 'users': ['alice'], 'minutes': 121}])
def test_off_must_name_known_users_and_expire(client, monkeypatch, payload):
    monkeypatch.setenv('ENV', 'demo')
    assert client.put('/api/admin/agent-gateway', headers=login(client, 'admin'), json=payload).status_code == 422


def test_legacy_global_off_row_is_ignored_even_in_a_lab(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    with get_db().connect() as conn:
        conn.execute("INSERT INTO bank_settings VALUES ('agent_gateway','\"off\"','x') ON CONFLICT(key) DO UPDATE SET value_json='\"off\"'")
    assert gateway_of(client, login(client))[0] == 'on'


def test_session_rows_are_ignored_outside_a_lab(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    switch(client, login(client, 'admin'), False, users=['alice'])
    monkeypatch.delenv('ENV')
    assert gateway_of(client, login(client))[0] == 'on'
