"""R1 variants after the fix (docs/release/week7-evidence/OUTBOX_TAKEOVER.md, "Sau khi sửa")."""
import re
import time
from app.main import app
from app.dependencies import get_db
from tests.conftest import sign_in
from tests.test_outbox_takeover import login_challenge


def test_charlie_sees_only_charlies_mail(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    for user in ('alice', 'bob'):
        login_challenge(client, user, user.capitalize() + '@2026')  # their live sign-in codes sit in the outbox
    charlie = sign_in(client, 'charlie', 'Charlie@2026')
    items = client.get('/api/dev/outbox', headers=charlie).json()['items']
    with get_db().connect() as conn:
        owners = {conn.execute('SELECT user_id FROM dev_outbox WHERE id=?', (m['id'],)).fetchone()[0] for m in items}
        others = [r[0] for r in conn.execute("SELECT id FROM dev_outbox WHERE user_id!='charlie'")]
    assert items and owners == {'charlie'}
    assert others and all(client.get('/api/dev/outbox/' + i, headers=charlie).status_code == 404 for i in others)


def test_wrong_foreign_or_expired_challenges_are_refused_then_rate_limited(client, monkeypatch):
    from app.api.routes import dev
    monkeypatch.setenv('ENV', 'demo')
    alice = login_challenge(client)
    wrong = client.post('/api/dev/outbox/challenge', json={'challenge_id': 'Q' * 43})
    assert wrong.status_code == 404
    # Bob's challenge only ever returns Bob's code, never Alice's.
    bob = login_challenge(client, 'bob', 'Bob@2026')
    bob_mail = client.post('/api/dev/outbox/challenge', json={'challenge_id': bob}).json()
    alice_mail = client.post('/api/dev/outbox/challenge', json={'challenge_id': alice}).json()
    with get_db().connect() as conn:
        assert conn.execute('SELECT user_id FROM dev_outbox WHERE id=?', (bob_mail['id'],)).fetchone()[0] == 'bob'
        conn.execute('UPDATE dev_outbox SET expires_at=? WHERE id=?', (int(time.time()) - 1, alice_mail['id']))
    assert alice_mail['code'] != bob_mail['code']
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': alice}).json()['code'] is None  # expired
    monkeypatch.setattr(dev, 'CHALLENGE_POLLS', 5)  # four calls are already counted above
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': bob}).status_code == 200
    assert client.post('/api/dev/outbox/challenge', json={'challenge_id': bob}).status_code == 429


def test_alices_reset_link_is_not_served_by_any_http_endpoint(client, monkeypatch):
    from fastapi.routing import APIRoute, _iter_routes_with_context
    monkeypatch.setenv('ENV', 'demo')
    monkeypatch.setenv('RESEARCH_SANDBOX_ENABLED', 'true')
    who = {'anonymous': {}, **{u: sign_in(client, u, u.capitalize() + '@2026') for u in ('bob', 'charlie', 'admin')}}
    assert client.post('/api/auth/forgot-password', json={'email': 'alice@novabank.test'}).status_code == 202
    with get_db().connect() as conn:
        mail_id, action = conn.execute("SELECT id,action_path FROM dev_outbox WHERE kind='RESET_PASSWORD' AND user_id='alice'").fetchone()
    token = action.split('token=')[1]
    probed = 0
    for route, context in _iter_routes_with_context(app.routes):  # includes lazily included routers, as in test_SEC_01
        if not isinstance(route, APIRoute) or 'GET' not in route.methods:
            continue
        path = re.sub(r'\{[^}]+\}', mail_id, getattr(context, 'path', None) or route.path)
        for headers in who.values():
            body = client.get(path, headers=headers).text
            assert token not in body, (route.path, headers)
            probed += 1
    # The one POST read, /api/dev/outbox/challenge, selects kind='LOGIN_OTP' by challenge; a reset mail has no challenge at all.
    with get_db().connect() as conn:
        assert conn.execute('SELECT challenge_id FROM dev_outbox WHERE id=?', (mail_id,)).fetchone()[0] is None
    assert probed > 100
