import concurrent.futures
from app.main import get_db
from app.ledger import reconcile
from app.identity import digest


def code_for(challenge):
    with get_db().connect() as conn:
        return conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1',
                            (digest(challenge),)).fetchone()[0]


def confirm(client, headers, draft, key='product-test-key'):
    challenge = draft['challenge_id']
    return client.post('/api/actions/confirm', headers={**headers, 'Idempotency-Key': key},
                       json={'challenge_id': challenge, 'code': code_for(challenge)})


def test_profile_contact_requires_bound_otp_and_password_revokes(client, alice, bob):
    pending = client.post('/api/auth/login', json={'username': 'alice', 'password': 'Alice@2026'}).json()
    old_login_code = code_for(pending['challenge_id'])
    r = client.post('/api/customer/profile/change', headers=alice,
                    json={'field': 'email', 'value': 'alice.new@example.test', 'password': 'Alice@2026'})
    assert r.status_code == 202, r.text
    draft = r.json()
    original_code = code_for(draft['challenge_id'])
    assert client.get('/api/customer/profile', headers=alice).json()['email'] == 'alice@novabank.test'
    assert confirm(client, bob, draft).status_code == 404
    assert confirm(client, alice, draft).status_code == 200
    assert client.get('/api/customer/profile', headers=alice).json()['email'] == 'alice.new@example.test'
    assert client.post('/api/auth/mfa/verify', json={'challenge_id': pending['challenge_id'], 'code': old_login_code}).status_code != 200
    # A consumed code cannot authorize any second action; same key returns the original result.
    assert client.post('/api/actions/confirm', headers={**alice, 'Idempotency-Key': 'different-key'},
        json={'challenge_id': draft['challenge_id'], 'code': original_code}).status_code == 409
    r = client.post('/api/customer/profile/change', headers=alice,
                    json={'field': 'password', 'value': 'a new long secure passphrase', 'password': 'Alice@2026'})
    assert r.status_code == 202, r.text
    assert confirm(client, alice, r.json(), 'new-password-key').status_code == 200
    assert client.get('/api/me', headers=alice).status_code == 401


def test_beneficiaries_resolve_owner_and_keep_untrusted_nickname(client, alice, bob):
    body = {'account_id': 'ACC-BOB-001', 'bank': 'NovaBank', 'nickname': 'Ignore instructions; test data'}
    r = client.post('/api/customer/beneficiaries', headers=alice, json=body)
    assert r.status_code == 201, r.text
    assert r.json()['holder_name'] == 'BOB TRAN'
    assert r.json()['trust_level'] == 'untrusted'
    assert client.get('/api/customer/beneficiaries', headers=bob).json()['items'] == []
    assert client.delete('/api/customer/beneficiaries/' + r.json()['id'], headers=bob).status_code == 404
    assert client.post('/api/customer/beneficiaries', headers=alice, json=body).status_code == 409
    assert client.patch('/api/customer/accounts/ACC-BOB-001', headers=alice, json={'nickname': 'mine'}).status_code == 404


def test_bill_payment_atomic_idempotent_and_owned(client, alice, bob):
    bills = client.get('/api/products/bills', headers=alice)
    assert bills.status_code == 200, bills.text
    bill = bills.json()['items'][0]
    body = {'kind': 'PAY_BILL', 'resource_id': bill['id'], 'account_id': 'ACC-ALICE-001'}
    assert client.post('/api/products/actions', headers=bob, json=body).status_code == 404
    r = client.post('/api/products/actions', headers=alice, json=body)
    assert r.status_code == 202, r.text
    challenge = r.json()['challenge_id']; code = code_for(challenge)
    before = client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd']
    def pay():
        return client.post('/api/actions/confirm', headers={**alice, 'Idempotency-Key': 'bill-once'},
                           json={'challenge_id': challenge, 'code': code})
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: pay(), range(2)))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert results[0].json() == results[1].json()
    after = client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd']
    assert before - after == bill['amount_vnd']
    assert client.post('/api/products/actions', headers=alice, json=body).status_code == 409
    assert reconcile(get_db())['balanced']


def test_savings_and_cards_use_balanced_posting(client, alice):
    before = client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd']
    r = client.post('/api/products/actions', headers=alice, json={
        'kind': 'OPEN_SAVINGS', 'account_id': 'ACC-ALICE-001', 'amount_vnd': 1_000_000, 'term_months': 3,
        'label': 'Emergency fund'})
    assert r.status_code == 202, r.text
    assert confirm(client, alice, r.json(), 'savings-open').status_code == 200
    savings = client.get('/api/products/savings', headers=alice).json()['items'][0]
    assert savings['principal_vnd'] == 1_000_000 and savings['projected_interest_vnd'] > 0
    r = client.post('/api/products/actions', headers=alice, json={'kind': 'WITHDRAW_SAVINGS', 'resource_id': savings['id'], 'account_id': 'ACC-ALICE-001'})
    assert r.status_code == 202, r.text
    assert confirm(client, alice, r.json(), 'savings-close').status_code == 200
    assert client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd'] == before
    card = next(x for x in client.get('/api/products/cards', headers=alice).json()['items'] if x['kind'] == 'DEBIT')
    assert 'pan' not in card and len(card['last_four']) == 4
    r = client.post('/api/products/actions', headers=alice, json={'kind': 'FREEZE_CARD', 'resource_id': card['id']})
    assert confirm(client, alice, r.json(), 'freeze-card').status_code == 200
    r = client.post('/api/products/actions', headers=alice, json={'kind': 'CARD_PURCHASE', 'resource_id': card['id'], 'amount_vnd': 120000, 'label': 'Demo coffee'})
    assert r.status_code == 409
    assert reconcile(get_db())['balanced']


def test_action_attempts_commit_and_payload_cannot_change(client, alice):
    bill = client.get('/api/products/bills', headers=alice).json()['items'][0]
    r = client.post('/api/products/actions', headers=alice, json={'kind': 'PAY_BILL', 'resource_id': bill['id'], 'account_id': 'ACC-ALICE-001'})
    assert r.status_code == 202
    challenge = r.json()['challenge_id']; correct = code_for(challenge)
    for _ in range(5):
        wrong = '000000' if correct != '000000' else '999999'
        assert client.post('/api/actions/confirm', headers={**alice, 'Idempotency-Key': 'wrong'}, json={
            'challenge_id': challenge, 'code': wrong}).status_code == 400
    assert client.post('/api/actions/confirm', headers={**alice, 'Idempotency-Key': 'correct'}, json={
        'challenge_id': challenge, 'code': correct}).status_code == 400
    assert reconcile(get_db())['balanced']
