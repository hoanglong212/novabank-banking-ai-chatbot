import json
import time
import pytest
from app.main import get_db
from app.ledger import reconcile
from app.identity import digest
from .test_customer_products import code_for, confirm


def action(client, alice, kind, **fields):
    r = client.post('/api/products/actions', headers=alice, json={'kind': kind, **fields})
    assert r.status_code == 202, r.text
    return r.json()


def test_credit_purchase_repayment_and_maturity_interest(client, alice):
    from app.posting import business_day
    from app.database import now
    month = business_day(now())[:7]
    initial_income = client.get('/api/insights?month=' + month, headers=alice).json()['income_vnd']
    cards = client.get('/api/products/cards', headers=alice).json()['items']
    credit = next(c for c in cards if c['kind'] == 'CREDIT')
    draft = action(client, alice, 'CARD_PURCHASE', resource_id=credit['id'], amount_vnd=200000, label='Book shop')
    assert confirm(client, alice, draft, 'credit-purchase').status_code == 200
    before = client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd']
    draft = action(client, alice, 'REPAY_CARD', resource_id=credit['id'], amount_vnd=200000)
    assert confirm(client, alice, draft, 'credit-repay').status_code == 200
    assert client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd'] == before - 200000
    draft = action(client, alice, 'OPEN_SAVINGS', account_id='ACC-ALICE-001', amount_vnd=1000000, term_months=6, label='Mature')
    result = confirm(client, alice, draft, 'mature-open').json()
    with get_db().connect() as conn:
        conn.execute("UPDATE savings SET maturity_date='2020-01-01' WHERE id=?", (result['resource_id'],))
    draft = action(client, alice, 'WITHDRAW_SAVINGS', resource_id=result['resource_id'])
    r = confirm(client, alice, draft, 'mature-close')
    assert r.status_code == 200, r.text
    assert client.get('/api/me', headers=alice).json()['accounts'][0]['balance_vnd'] == before - 200000 + 25000
    assert client.get('/api/insights?month=' + month, headers=alice).json()['income_vnd'] == initial_income + 25000
    assert reconcile(get_db())['balanced']


def test_valid_otp_does_not_bypass_new_card_state_or_funds(client, alice):
    card = next(c for c in client.get('/api/products/cards', headers=alice).json()['items'] if c['kind'] == 'DEBIT')
    purchase = action(client, alice, 'CARD_PURCHASE', resource_id=card['id'], amount_vnd=100000, label='Coffee')
    freeze = action(client, alice, 'FREEZE_CARD', resource_id=card['id'])
    assert confirm(client, alice, freeze, 'freeze').status_code == 200
    assert confirm(client, alice, purchase, 'purchase').status_code == 409
    unlock = action(client, alice, 'UNFREEZE_CARD', resource_id=card['id'])
    assert confirm(client, alice, unlock, 'unlock').status_code == 200
    assert confirm(client, alice, purchase, 'purchase').status_code == 200
    assert reconcile(get_db())['balanced']


def test_two_valid_bill_challenges_cannot_double_pay_and_expiry_is_enforced(client, alice):
    bill = client.get('/api/products/bills', headers=alice).json()['items'][0]
    fields = dict(resource_id=bill['id'], account_id='ACC-ALICE-001')
    first, second = action(client, alice, 'PAY_BILL', **fields), action(client, alice, 'PAY_BILL', **fields)
    assert confirm(client, alice, first, 'bill1').status_code == 200
    assert confirm(client, alice, second, 'bill2').status_code == 409
    draft = action(client, alice, 'OPEN_SAVINGS', account_id='ACC-ALICE-001', amount_vnd=100000, term_months=3)
    code = code_for(draft['challenge_id'])
    with get_db().connect() as conn:
        conn.execute('UPDATE action_challenges SET expires_at=? WHERE id=?', (int(time.time())-1, digest(draft['challenge_id'])))
    r = client.post('/api/actions/confirm', headers={**alice, 'Idempotency-Key': 'expired'}, json={'challenge_id': draft['challenge_id'], 'code': code})
    assert r.status_code == 400
    assert reconcile(get_db())['balanced']


def test_qr_signed_png_roundtrip_rejects_tamper_and_real_payment_data(client, alice):
    r = client.post('/api/vietqr', headers=alice, json={'bank': 'NovaBank', 'account_no': 'ACC-ALICE-001', 'amount_vnd': 10000})
    assert r.status_code == 200, r.text
    qr = r.json(); assert qr['image'].startswith('data:image/png;base64,')
    for body in ({'payload': qr['payload']}, {'image_base64': qr['image'].split(',')[1]}):
        decoded = client.post('/api/qr/decode', headers=alice, json=body)
        assert decoded.status_code == 200 and decoded.json()['account_no'] == 'ACC-ALICE-001'
    assert client.post('/api/qr/decode', headers=alice, json={'payload': qr['payload'] + 'a'}).status_code == 422
    assert client.post('/api/qr/decode', headers=alice, json={'payload': '000201NAPASREALPAYMENT'}).status_code == 422


def test_security_headers_body_limit_and_untrusted_origin(client, alice):
    r = client.get('/api/me', headers=alice)
    assert r.headers['Cache-Control'] == 'no-store'
    assert "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
    assert r.headers['X-Content-Type-Options'] == 'nosniff'
    assert client.post('/api/support/tickets', headers=alice, content=b'x' * (4*1024*1024+1)).status_code == 413
    r = client.options('/api/me', headers={'Origin': 'https://untrusted.invalid', 'Access-Control-Request-Method': 'GET'})
    assert r.status_code == 400 and 'access-control-allow-origin' not in r.headers
