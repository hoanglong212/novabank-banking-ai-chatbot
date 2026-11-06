"""Expectations explicitly ratified by the user on 2026-11-01."""
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


@pytest.mark.parametrize('extra', [{'role':'admin'}, {'balance':1000000}, {'balance_vnd':1000000}])
def test_AUTH_03_server_owned_registration_fields_rejected_422(client, extra):
    payload = {'username':'spec_user','name':'Spec User','email':'spec@example.test','password':'A strong passphrase 2026!', **extra}
    assert client.post('/api/auth/register', json=payload).status_code == 422
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id='spec_user'").fetchone()[0] == 0


def test_AI_13_delegated_confirmation_is_denied_without_effects(client):
    who = login(client); _, run, token = run_for(client, who)
    draft = client.post('/api/transfers', headers=who, json={'to_account':'ACC-BOB-001','amount_vnd':2000}).json()
    before = client.get('/api/me', headers=who).json()['accounts']
    response = client.post('/api/transfers/'+draft['id']+'/confirm', headers=token, json={'otp':transfer_code(draft)})
    assert response.status_code in (401,403)  # Either denial status is accepted; no effects are mandatory.
    assert client.get('/api/me', headers=who).json()['accounts'] == before
    with get_db().connect() as conn:
        assert conn.execute('SELECT status,otp_attempts FROM transfers WHERE id=?', (draft['id'],)).fetchone()[:] == ('PENDING_OTP',0)

from tests.conftest import transfer_code
