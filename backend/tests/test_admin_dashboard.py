from datetime import datetime, timezone
from .conftest import sign_in


def add_transfer(conn, identity, stamp, amount, status='COMPLETED', internal=True, settlement=None):
    conn.execute('''INSERT INTO transfers (id,owner_id,from_account,to_bank,to_account,to_name,internal,
        amount_vnd,content,status,created_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
        (identity, 'alice', 'ACC-ALICE-001', 'NovaBank' if internal else 'Demo Bank A', 'ACC-BOB-001',
         'BOB TRAN', int(internal), amount, 'Dashboard test', status, stamp, stamp if status == 'COMPLETED' else None))
    if settlement:
        conn.execute('INSERT INTO interbank_settlements (transfer_id,status,due_at) VALUES (?,?,?)',
                     (identity, settlement, stamp))


def test_dashboard_counts_unique_settled_transfers_and_vietnam_days(client, monkeypatch):
    from app import admin_dashboard
    from app.dependencies import get_db
    monkeypatch.setattr(admin_dashboard, 'utc_now', lambda: datetime(2026, 11, 8, 5, tzinfo=timezone.utc))
    with get_db().connect() as conn:
        add_transfer(conn, 'local', '2026-11-07T18:00:00+00:00', 100000)
        add_transfer(conn, 'external', '2026-11-07T18:00:00+00:00', 200000, internal=False, settlement='COMPLETED')
        add_transfer(conn, 'failed', '2026-11-07T18:00:00+00:00', 300000, internal=False, settlement='FAILED')
        add_transfer(conn, 'pending', '2026-11-01T12:00:00+00:00', 400000, internal=False, settlement='PENDING')
        add_transfer(conn, 'draft', '2026-11-07T18:00:00+00:00', 900000, status='PENDING_OTP')
        add_transfer(conn, 'previous', '2026-11-01T12:00:00+00:00', 500000)
    admin = sign_in(client, 'admin', 'Admin@2026')
    response = client.get('/api/admin/overview?days=7', headers=admin)
    assert response.status_code == 200, response.text
    data = response.json()['dashboard']
    assert data['period']['from_date'] == '2026-11-02'
    assert data['metrics']['volume_vnd'] == 300000
    assert data['metrics']['completed'] == 2 and data['metrics']['failed'] == 1
    assert data['metrics']['success_rate'] == 66.7
    assert data['previous']['volume_vnd'] == 500000
    assert data['snapshot']['pending_settlements'] == 1
    assert len(data['daily']) == 7
    assert data['daily'][-1] == {'date': '2026-11-08', 'internal_vnd': 100000, 'external_vnd': 200000, 'completed': 2}
    assert len(data['queues']['pending']) == 1 and data['queues']['pending'][0]['status'] == 'PENDING'
    assert data['queues']['failed'][0]['status'] == 'FAILED'
    assert all(item['id'] != 'draft' for item in data['recent'])
    assert 'otp_hash' not in str(data) and 'secret_text' not in str(data)


def test_dashboard_empty_period_permissions_and_bounded_queues(client, alice):
    from app.dependencies import get_db
    admin = sign_in(client, 'admin', 'Admin@2026')
    empty = client.get('/api/admin/overview?days=30', headers=admin).json()['dashboard']
    assert empty['metrics']['volume_vnd'] == 0 and empty['metrics']['success_rate'] is None
    assert len(empty['daily']) == 30 and all(day['completed'] == 0 for day in empty['daily'])
    assert empty['recent'] == []
    assert client.get('/api/admin/overview', headers=alice).status_code == 403
    auditor = sign_in(client, 'auditor', 'Auditor@2026')
    assert client.get('/api/admin/overview?days=90', headers=auditor).status_code == 200
    assert client.post('/api/admin/reconcile', headers=auditor).status_code == 403
    assert client.get('/api/admin/overview?days=999', headers=admin).status_code == 422
    with get_db().connect() as conn:
        for i in range(25):
            add_transfer(conn, f'queued-{i}', '2026-01-01T00:00:00+00:00', 1000, internal=False, settlement='PENDING')
    result = client.get('/api/admin/overview', headers=admin).json()
    assert result['dashboard']['snapshot']['pending_settlements'] == 25
    assert len(result['dashboard']['queues']['pending']) == 20
    assert all(key in result for key in ('users', 'accounts', 'transactions', 'support_tickets', 'reconciliation'))
