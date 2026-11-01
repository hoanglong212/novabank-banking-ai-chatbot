"""Receipt, customer notifications and staff authorization over real SQLite posting."""
import json
import sqlite3

import pytest

from app.main import get_db
from .conftest import sign_in
from .test_banking_core import confirm
from .test_transfers import draft
from .test_ledger import report


def pay(client, alice, **kwargs):
    t = draft(client, alice, **kwargs).json()
    r = confirm(client, alice, t, 'receipt-' + t['id'])
    assert r.status_code == 200, r.text
    return t, r.json()


def test_transaction_details_record_both_balances_and_do_not_change(client, alice, bob):
    t, receipt = pay(client, alice)
    detail = client.get('/api/transactions/' + receipt['transaction_id'], headers=alice)
    assert detail.status_code == 200
    row = detail.json()
    assert (row['transfer_id'], row['balance_after_vnd'], row['fee_vnd']) == (t['id'], 12_300_000, 0)
    assert row['counterparty_name'] == 'BOB TRAN'
    bob_rows = client.get('/api/transactions', headers=bob).json()['items']
    incoming = next(r for r in bob_rows if r['transfer_id'] == t['id'])
    assert (incoming['balance_after_vnd'], incoming['direction']) == (8_950_000, 'in')
    pay(client, alice)
    assert client.get('/api/transactions/' + receipt['transaction_id'], headers=alice).json() == row
    with get_db().connect() as conn:
        with pytest.raises(sqlite3.IntegrityError, match='IMMUTABLE'):
            conn.execute('UPDATE transaction_details SET balance_after_vnd=0')
    assert report(get_db())['balanced']


def test_transaction_queries_are_owner_scoped_and_paginated(client, alice, bob):
    assert client.get('/api/transactions/TX-2001', headers=alice).status_code == 404
    assert client.get('/api/transactions/missing', headers=alice).status_code == 404
    page1 = client.get('/api/transactions?direction=out&limit=1&offset=0', headers=alice).json()
    page2 = client.get('/api/transactions?direction=out&limit=1&offset=1', headers=alice).json()
    assert page1['total'] == page2['total'] == 3
    assert page1['items'][0]['id'] != page2['items'][0]['id']
    rows = client.get('/api/transactions?from_date=2026-10-25&to_date=2026-10-25&q=Electricity', headers=alice).json()
    assert [r['id'] for r in rows['items']] == ['TX-1002']
    for q in ["' OR 1=1 --", '%', '_', 'TX-2001']:
        assert client.get('/api/transactions', headers=alice, params={'q': q}).json()['total'] == 0
    assert client.get('/api/transactions?account_id=ACC-BOB-001', headers=alice).status_code == 404
    for query in ['limit=101', 'offset=-1', 'direction=evil', 'from_date=bad']:
        assert client.get('/api/transactions?' + query, headers=alice).status_code == 422
    assert client.get('/api/transactions?from_date=2026-11-01&to_date=2026-10-01', headers=alice).status_code == 400


def test_legacy_transaction_does_not_invent_balance(client, alice):
    response = client.get('/api/transactions/TX-1001', headers=alice)
    assert response.status_code == 200
    assert response.json()['balance_after_vnd'] is None
    assert response.json()['transfer_id'] is None


def test_pdf_is_owned_completed_only_and_stable(client, alice, bob):
    _, receipt = pay(client, alice)
    path = '/api/transactions/' + receipt['transaction_id'] + '/receipt.pdf'
    first = client.get(path, headers=alice)
    assert first.status_code == 200
    assert first.headers['content-type'] == 'application/pdf'
    assert first.content.startswith(b'%PDF-') and b'%%EOF' in first.content[-30:]
    assert receipt['transaction_id'] in first.headers['content-disposition']
    assert first.headers['cache-control'] == 'no-store'
    assert client.get(path, headers=bob).status_code == 404
    assert client.get(path).status_code == 401
    assert client.get('/api/transactions/TX-1002/receipt.pdf', headers=alice).status_code == 409
    pay(client, alice)
    assert client.get(path, headers=alice).content == first.content


def test_notifications_created_once_and_marked_read_only_by_owner(client, alice, bob):
    t, _ = pay(client, alice)
    assert confirm(client, alice, t, 'receipt-' + t['id']).status_code == 200
    a = client.get('/api/notifications', headers=alice).json()
    b = client.get('/api/notifications', headers=bob).json()
    assert a['unread_count'] == b['unread_count'] == 1
    assert len(a['items']) == len(b['items']) == 1
    assert a['items'][0]['kind'] == 'MONEY_OUT'
    item = b['items'][0]
    assert item['kind'] == 'MONEY_IN' and '200,000' in item['body']
    assert client.patch('/api/notifications/' + item['id'] + '/read', headers=alice).status_code == 404
    read = client.patch('/api/notifications/' + item['id'] + '/read', headers=bob)
    assert read.status_code == 200 and read.json()['read_at']
    assert client.patch('/api/notifications/' + item['id'] + '/read', headers=bob).json() == read.json()
    assert client.get('/api/notifications', headers=bob).json()['unread_count'] == 0
    assert client.get('/api/notifications', headers=alice).json()['unread_count'] == 1


def test_notifications_and_details_rollback_with_failed_posting(client, alice):
    t = draft(client, alice).json()
    with get_db().connect() as conn:
        conn.execute("""CREATE TRIGGER fail_notification BEFORE INSERT ON notifications
                        WHEN NEW.kind='MONEY_IN' BEGIN SELECT RAISE(ABORT,'simulated failure'); END""")
    assert confirm(client, alice, t).status_code == 503
    with get_db().connect() as conn:
        for table in ('notifications', 'transaction_details'):
            assert conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] == 0
    assert report(get_db())['balanced']


def test_mark_all_read_does_not_affect_other_customer(client, alice, bob):
    pay(client, alice)
    pay(client, alice)
    response = client.post('/api/notifications/read-all', headers=bob)
    assert response.status_code == 200 and response.json()['updated'] == 2
    assert client.get('/api/notifications', headers=bob).json()['unread_count'] == 0
    assert client.get('/api/notifications', headers=alice).json()['unread_count'] == 2


@pytest.mark.parametrize('username,password,allowed', [
    ('alice', 'Alice@2026', False), ('bob', 'Bob@2026', False), ('charlie', 'Charlie@2026', False),
    ('support', 'Support@2026', False), ('operations', 'Operations@2026', True),
    ('auditor', 'Auditor@2026', True), ('admin', 'Admin@2026', True),
])
def test_role_matrix_for_financial_admin(client, username, password, allowed):
    headers = sign_in(client, username, password)
    response = client.get('/api/admin/transactions', headers=headers)
    assert response.status_code == (200 if allowed else 403)
    if allowed:
        assert response.json()['total'] == 7
        assert {r['owner_id'] for r in response.json()['items']} == {'alice', 'bob'}
    me = client.get('/api/me', headers=headers).json()
    assert me['role'] in ('customer', 'support', 'operations', 'auditor', 'admin')


@pytest.mark.parametrize('username', ['support', 'operations', 'auditor', 'admin'])
def test_staff_cannot_use_customer_tools_or_transfer(client, username):
    headers = sign_in(client, username, username.capitalize() + '@2026')
    assert draft(client, headers).status_code == 403
    assert client.post('/api/conversations', headers=headers, json={}).status_code == 403
    assert client.get('/api/transactions', headers=headers).status_code == 403
    assert client.get('/api/me', headers=headers).json()['accounts'] == []


def test_admin_search_audit_and_third_user_isolation(client, alice):
    t, receipt = pay(client, alice)
    admin = sign_in(client, 'admin', 'Admin@2026')
    charlie = sign_in(client, 'charlie', 'Charlie@2026')
    rows = client.get('/api/admin/transactions', headers=admin, params={'q': receipt['transaction_id']}).json()
    assert rows['total'] == 1 and rows['items'][0]['transfer_id'] == t['id']
    audit_path = '/api/admin/transfers/' + t['id'] + '/audit'
    events = client.get(audit_path, headers=admin).json()['items']
    assert any(e['action'] == 'TRANSFER_COMPLETED' and e['after_balance_vnd'] == 12_300_000 for e in events)
    assert not any(key in json.dumps(events) for key in ['otp_hash', 'password_hash', 'access_token'])
    assert client.get(audit_path, headers=alice).status_code == 403
    assert client.get('/api/admin/transfers/missing/audit', headers=admin).status_code == 404
    assert client.get('/api/transactions/' + receipt['transaction_id'], headers=charlie).status_code == 404
    assert client.get('/api/notifications', headers=charlie).json()['items'] == []
    assert client.get('/api/transactions', headers=charlie).json()['items'] == []
    assert report(get_db())['balanced']


def test_experience_migration_preserves_posting_and_unread_state(client, alice):
    t, receipt = pay(client, alice)
    get_db().initialize()
    assert client.get('/api/notifications', headers=alice).json()['unread_count'] == 1
    assert client.get('/api/transactions/' + receipt['transaction_id'], headers=alice).json()['balance_after_vnd'] == 12_300_000
    assert report(get_db())['balanced']


def test_v1_migration_backfills_only_authoritative_payer_snapshot(client, alice, bob, monkeypatch):
    from app import posting
    # Reproduce the v1 schema before creating a real ledger-backed transfer.
    with get_db().connect() as conn:
        conn.execute('DROP TABLE notifications')
        conn.execute('DROP TABLE transaction_details')
        conn.execute('DELETE FROM schema_migrations WHERE version=2')
    with monkeypatch.context() as previous_version:
        previous_version.setattr(posting, '_record_detail_and_notification', lambda *args: None)
        t, receipt = pay(client, alice)
    with get_db().connect() as conn:
        ledger_before = [tuple(r) for r in conn.execute('SELECT * FROM ledger_entries ORDER BY id')]
    get_db().initialize()
    payer = client.get('/api/transactions/' + receipt['transaction_id'], headers=alice).json()
    assert payer['balance_after_vnd'] == 12_300_000 and payer['transfer_id'] == t['id']
    incoming = client.get('/api/transactions', headers=bob).json()['items'][0]
    assert incoming['balance_after_vnd'] is None and incoming['transfer_id'] is None
    assert client.get('/api/notifications', headers=alice).json()['total'] == 0
    with get_db().connect() as conn:
        assert [tuple(r) for r in conn.execute('SELECT * FROM ledger_entries ORDER BY id')] == ledger_before
    assert report(get_db())['balanced']


def test_role_claims_cannot_override_server_permissions(client, alice):
    import jwt
    from app.auth import SECRET, ISSUER
    claims = jwt.decode(alice['Authorization'][7:], SECRET, algorithms=['HS256'], issuer=ISSUER)
    claims.update(role='admin', permissions=['admin:transactions:read', 'admin:audit:read'])
    headers = {'Authorization': 'Bearer ' + jwt.encode(claims, SECRET, algorithm='HS256')}
    assert client.get('/api/admin/transactions', headers=headers).status_code == 403
    assert client.get('/api/me', headers=headers).json()['role'] == 'customer'
