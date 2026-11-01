from app.main import get_db
from app.action_security import notify
from app.identity import transaction
from app.database import now


def test_optional_notifications_respect_owner_settings_and_critical_alerts_remain(client, alice, bob):
    path = '/api/customer/notification-preferences'
    assert client.get(path, headers=alice).json() == {'bill_reminders': True, 'budget_alerts': True}
    assert client.put(path, headers=alice, json={'bill_reminders': False, 'budget_alerts': False}).status_code == 200
    assert client.get(path, headers=bob).json() == {'bill_reminders': True, 'budget_alerts': True}
    assert client.put(path, headers=alice, json={'bill_reminders': False, 'budget_alerts': False, 'security_alerts': False}).status_code == 422
    db = get_db()
    with transaction(db) as conn:
        for owner in ('alice', 'bob'):
            for kind in ('BILL','BUDGET','SECURITY','MONEY_IN'):
                notify(conn, owner, kind, 'Preference test', 'Synthetic event', now())
        alice_kinds = {r[0] for r in conn.execute("SELECT kind FROM service_notifications WHERE owner_id='alice' AND title='Preference test'")}
        bob_kinds = {r[0] for r in conn.execute("SELECT kind FROM service_notifications WHERE owner_id='bob' AND title='Preference test'")}
    assert alice_kinds == {'SECURITY','MONEY_IN'}
    assert bob_kinds == {'BILL','BUDGET','SECURITY','MONEY_IN'}
