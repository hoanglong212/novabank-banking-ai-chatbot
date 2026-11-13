"""B5: /api/transfers/{id}/confirm requires the signed confirmation token for exactly that draft."""
import base64
from datetime import datetime
import json
import jwt
import pytest
from app import auth, transfers
from app.dependencies import get_db
from tests.conftest import transfer_code



def draft(client, who, account='ACC-BOB-001', amount=10_000):
    response = client.post('/api/transfers', headers=who, json={'to_account': account, 'amount_vnd': amount})
    assert response.status_code == 201, response.text
    return response.json()


def confirm(client, who, d, token, key=None):
    headers = {**who, **({'Idempotency-Key': key} if key else {})}
    return client.post(f'/api/transfers/{d["id"]}/confirm', headers=headers, json={'otp': transfer_code(d), 'confirm_token': token})


def claims_of(token):
    return jwt.decode(token, options={'verify_signature': False})


def resign(token, **changes):
    return jwt.encode({**claims_of(token), **changes}, auth.TRANSFER_TOKEN_KEY, algorithm='HS256')


def test_draft_carries_a_token_bound_to_its_parameters(client, alice):
    d = draft(client, alice)
    c = claims_of(d['confirm_token'])
    assert (c['aud'], c['sub'], c['owner_id'], c['to_bank'], c['to_account'], c['amount_vnd']) == (
        'transfer-confirm', d['id'], 'alice', 'NovaBank', 'ACC-BOB-001', 10_000)
    assert 0 < c['exp'] - c['iat'] <= 300 and len(c['jti']) == 32
    # The token never leaks into storage or the draft's public fields.
    with get_db().connect() as conn:
        assert d['confirm_token'] not in json.dumps([dict(r) for r in conn.execute('SELECT * FROM transfers')])


def test_valid_token_confirms_once(client, alice):
    d = draft(client, alice)
    assert confirm(client, alice, d, d['confirm_token']).json()['status'] == 'COMPLETED'


def test_missing_token_is_refused(client, alice):
    d = draft(client, alice)
    response = confirm(client, alice, d, None)
    assert (response.status_code, response.json()['detail']) == (403, 'TOKEN_REQUIRED')


@pytest.mark.parametrize('forge', [
    lambda t: t[:-4] + ('AAAA' if not t.endswith('AAAA') else 'BBBB'),                        # broken signature
    lambda t: jwt.encode(claims_of(t), 'not-the-transfer-key-' + 'x' * 32, algorithm='HS256'),  # wrong key
    lambda t: jwt.encode(claims_of(t), auth.SECRET, algorithm='HS256'),                        # the login JWT key (R8)
    lambda t: resign(t, aud='novabank-agent-tools'),                                         # wrong audience
    lambda t: 'garbage',
])
def test_bad_signature_or_audience_is_refused(client, alice, forge):
    d = draft(client, alice)
    response = confirm(client, alice, d, forge(d['confirm_token']))
    assert (response.status_code, response.json()['detail']) == (403, 'TOKEN_INVALID')


def test_amount_or_recipient_edited_inside_the_token_breaks_the_signature(client, alice):
    d = draft(client, alice)
    header, payload, signature = d['confirm_token'].split('.')
    for change in ({'amount_vnd': 9_000_000}, {'to_account': 'ACC-CHARLIE-001'}):
        edited = base64.urlsafe_b64encode(json.dumps({**claims_of(d['confirm_token']), **change}).encode()).decode().rstrip('=')
        assert confirm(client, alice, d, '.'.join((header, edited, signature))).json()['detail'] == 'TOKEN_INVALID'


@pytest.mark.parametrize('change', [{'amount_vnd': 9_000_000}, {'to_account': 'ACC-CHARLIE-001'}, {'to_bank': 'VCB'}, {'owner_id': 'bob'}])
def test_token_for_other_parameters_is_refused_even_when_signed(client, alice, change):
    d = draft(client, alice)
    assert confirm(client, alice, d, resign(d['confirm_token'], **change)).json()['detail'] == 'TOKEN_MISMATCH'


def test_draft_changed_after_the_token_was_issued_is_refused(client, alice):
    d = draft(client, alice)
    with get_db().connect() as conn:
        conn.execute("UPDATE transfers SET amount_vnd=5000000, to_account='ACC-CHARLIE-001' WHERE id=?", (d['id'],))
    assert confirm(client, alice, d, d['confirm_token']).json()['detail'] == 'TOKEN_MISMATCH'
    with get_db().connect() as conn:
        assert conn.execute('SELECT status FROM transfers WHERE id=?', (d['id'],)).fetchone()[0] == 'PENDING_OTP'


def test_expired_token_is_refused(client, alice):
    d = draft(client, alice)
    c = claims_of(d['confirm_token'])
    assert confirm(client, alice, d, resign(d['confirm_token'], exp=c['iat'] - 1)).json()['detail'] == 'TOKEN_EXPIRED'
    # A token minted later than the draft still dies with the draft.
    assert c['exp'] <= int(datetime.fromisoformat(transfers._expires_at(get_db().get_transfer(d['id'], 'alice'))).timestamp())


def test_reused_token_is_refused(client, alice):
    d = draft(client, alice)
    assert confirm(client, alice, d, d['confirm_token'], key='first').status_code == 200
    replay = confirm(client, alice, d, d['confirm_token'], key='second')
    assert (replay.status_code, replay.json()['detail']) == (409, 'TOKEN_REPLAYED')
    # The same idempotency key still returns the stored receipt instead of a second payment.
    assert confirm(client, alice, d, d['confirm_token'], key='first').json()['status'] == 'COMPLETED'
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM transfer_token_uses WHERE transfer_id=?', (d['id'],)).fetchone()[0] == 1


def test_another_users_token_is_refused(client, alice, bob):
    mine, theirs = draft(client, alice), draft(client, bob, account='ACC-ALICE-001')
    assert confirm(client, alice, mine, theirs['confirm_token']).json()['detail'] == 'TOKEN_MISMATCH'
    # Bob cannot touch Alice's draft at all, with or without her token.
    assert confirm(client, bob, mine, mine['confirm_token']).status_code == 404


def test_wrong_otp_keeps_the_token_usable(client, alice):
    d = draft(client, alice)
    wrong = '000000' if transfer_code(d) != '000000' else '111111'
    bad = client.post(f'/api/transfers/{d["id"]}/confirm', headers=alice, json={'otp': wrong, 'confirm_token': d['confirm_token']})
    assert bad.json()['detail'] == 'OTP_INVALID'
    assert confirm(client, alice, d, d['confirm_token']).json()['status'] == 'COMPLETED'


def test_reloading_the_draft_gets_a_fresh_token_until_it_completes(client, alice):
    d = draft(client, alice)
    again = client.get('/api/transfers/' + d['id'], headers=alice).json()['confirm_token']
    assert claims_of(again)['jti'] != claims_of(d['confirm_token'])['jti']
    assert confirm(client, alice, d, again).json()['status'] == 'COMPLETED'
    assert 'confirm_token' not in client.get('/api/transfers/' + d['id'], headers=alice).json()
