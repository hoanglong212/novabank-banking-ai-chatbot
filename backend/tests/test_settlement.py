from app.main import get_db
from app.ledger import reconcile
from .test_transfers import draft, balance


def test_pending_external_and_reversal_with_fee(client, alice):
    from app.settlement import process_due
    from app.posting import business_day
    from app.database import now
    month = business_day(now())[:7]
    initial = client.get('/api/insights?month=' + month, headers=alice).json()
    with get_db().connect() as conn:
        conn.execute("UPDATE bank_settings SET value_json='1000' WHERE key='transfer_fee_vnd'")
    before = balance(client, alice)
    t = draft(client, alice, to_bank='Demo Bank A', to_account='1234560000').json()
    assert t['fee_vnd'] == 1000
    r = client.post(f'/api/transfers/{t["id"]}/confirm', headers={**alice, 'Idempotency-Key': 'external-fail'}, json={'otp': t['demo_otp']})
    assert r.status_code == 200 and r.json()['status'] == 'PENDING', r.text
    assert balance(client, alice) == before - 201000
    assert client.get('/api/transactions/' + r.json()['transaction_id'], headers=alice).json()['status'] == 'PENDING'
    assert process_due(get_db(), force=True)['reversed'] == 1
    assert balance(client, alice) == before
    assert process_due(get_db(), force=True)['reversed'] == 0
    assert client.get('/api/transactions/' + r.json()['transaction_id'], headers=alice).json()['status'] == 'FAILED'
    assert reconcile(get_db())['balanced']
    final = client.get('/api/insights?month=' + month, headers=alice).json()
    assert (final['income_vnd'], final['expense_vnd']) == (initial['income_vnd'], initial['expense_vnd'])


def test_successful_external_is_completed_by_worker(client, alice):
    from app.settlement import process_due
    t = draft(client, alice, to_bank='Demo Bank B', to_account='1234567890').json()
    r = client.post(f'/api/transfers/{t["id"]}/confirm', headers=alice, json={'otp': t['demo_otp']})
    assert r.json()['status'] == 'PENDING'
    assert process_due(get_db(), force=True)['completed'] == 1
    assert client.get('/api/transactions/' + r.json()['transaction_id'], headers=alice).json()['status'] == 'COMPLETED'
    assert reconcile(get_db())['balanced']
