from app import products
from datetime import datetime
from tests.test_customer_products import confirm
from tests.test_product_invariants import action


def test_credit_spending_uses_vietnam_month_at_utc_boundary(client, alice, monkeypatch):
    cards = client.get('/api/products/cards', headers=alice).json()['items']
    credit = next(c for c in cards if c['kind'] == 'CREDIT')
    before = client.get('/api/insights?month=2030-11', headers=alice).json()['expense_vnd']
    execute = products.execute
    # Freeze only the product posting clock; authentication and OTP expiry stay real.
    seconds = int(datetime.fromisoformat('2030-10-31T17:30:00+00:00').timestamp())
    monkeypatch.setattr(products, 'execute', lambda conn, user, kind, payload, journal, stamp: execute(conn, user, kind, payload, journal, seconds))
    draft = action(client, alice, 'CARD_PURCHASE', resource_id=credit['id'], amount_vnd=100000, label='Timezone audit purchase')
    assert confirm(client, alice, draft, 'timezone-audit').status_code == 200
    # This instant is November 1 at 00:30 in Vietnam, October 31 in UTC.
    result = client.get('/api/insights?month=2030-11', headers=alice)
    assert result.status_code == 200
    assert result.json()['expense_vnd'] - before == 100000
    assert {'date': '2030-11-01', 'amount_vnd': 100000} in result.json()['daily']
