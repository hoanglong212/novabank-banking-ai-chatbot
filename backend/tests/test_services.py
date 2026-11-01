import base64
from .conftest import sign_in


def test_ticket_workflow_and_attachment_isolation(client, alice, bob):
    r = client.post('/api/support/tickets', headers=alice, json={'subject': 'Payment question', 'description': 'Please check my simulated bill.', 'category': 'PAYMENT'})
    assert r.status_code == 201, r.text
    ticket = r.json()['id']
    assert client.get('/api/support/tickets/' + ticket, headers=bob).status_code == 404
    r = client.post(f'/api/support/tickets/{ticket}/attachments', headers=alice, json={
        'name': 'note.txt', 'content_base64': base64.b64encode(b'Customer test note').decode()})
    assert r.status_code == 201, r.text
    attachment = r.json()['id']
    assert client.get('/api/support/attachments/' + attachment, headers=bob).status_code == 404
    r = client.get('/api/support/attachments/' + attachment, headers=alice)
    assert r.content == b'Customer test note' and 'attachment;' in r.headers['Content-Disposition']
    staff = sign_in(client, 'support', 'Support@2026')
    assert client.patch('/api/support/tickets/' + ticket, headers=staff, json={'status': 'IN_PROGRESS', 'assigned_to': 'support'}).status_code == 200
    assert client.post(f'/api/support/tickets/{ticket}/messages', headers=staff, json={'body': 'We are investigating.'}).status_code == 201
    assert len(client.get('/api/support/tickets/' + ticket, headers=alice).json()['messages']) == 1
    assert client.patch('/api/support/tickets/' + ticket, headers=alice, json={'status': 'CLOSED'}).status_code == 403
    assert client.post(f'/api/support/tickets/{ticket}/attachments', headers=alice, json={'name': 'bad.html', 'content_base64': base64.b64encode(b'<script>test</script>').decode()}).status_code == 422


def test_admin_permissions_settings_and_revocation(client, alice):
    assert client.get('/api/admin/overview', headers=alice).status_code == 403
    auditor = sign_in(client, 'auditor', 'Auditor@2026')
    assert client.get('/api/admin/overview', headers=auditor).status_code == 200
    assert client.patch('/api/admin/settings', headers=auditor, json={'transfer_fee_vnd': 1000}).status_code == 403
    admin = sign_in(client, 'admin', 'Admin@2026')
    assert client.patch('/api/admin/settings', headers=admin, json={'transfer_fee_vnd': 1000}).status_code == 200
    assert client.patch('/api/admin/settings', headers=admin, json={'transfer_fee_vnd': -1}).status_code == 422
    assert client.patch('/api/admin/users/alice', headers=admin, json={'status': 'DISABLED'}).status_code == 200
    assert client.get('/api/me', headers=alice).status_code == 401


def test_analytics_budget_statement_and_goal_are_owner_scoped(client, alice, bob):
    r = client.get('/api/insights?month=2026-10', headers=alice)
    assert r.status_code == 200, r.text
    assert r.json()['income_vnd'] == 15000000
    assert r.json()['expense_vnd'] == 345000  # Pending bill is excluded.
    r = client.put('/api/insights/budgets', headers=alice, json={'month': '2026-10', 'category': 'food', 'amount_vnd': 20000})
    assert r.status_code == 200, r.text
    alerts = client.get('/api/notifications', headers=alice).json()['items']
    assert any(x['kind'] == 'BUDGET' for x in alerts)
    assert not any(x['kind'] == 'BUDGET' for x in client.get('/api/notifications', headers=bob).json()['items'])
    for extension, magic in [('csv', b'\xef\xbb\xbf'), ('pdf', b'%PDF')]:
        r = client.get(f'/api/statements.{extension}?from_date=2026-10-01&to_date=2026-10-31', headers=alice)
        assert r.status_code == 200 and r.content.startswith(magic), r.text[:150]
        if extension == 'csv':
            assert b'TX-2001' not in r.content
    r = client.post('/api/savings-goals', headers=alice, json={'label': 'Holiday', 'target_vnd': 5000000, 'target_date': '2027-01-01'})
    assert r.status_code == 201, r.text
    assert client.get('/api/savings-goals', headers=bob).json()['items'] == []
