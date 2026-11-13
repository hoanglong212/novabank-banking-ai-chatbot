from app import vietqr


def test_goal_can_be_edited_and_remains_owner_scoped(client, alice, bob):
    body = {'label': 'Trip', 'target_vnd': 2000000, 'target_date': '2030-01-01'}
    goal = client.post('/api/savings-goals', headers=alice, json=body).json()['id']
    updated = {**body, 'label': 'New trip', 'target_vnd': 3000000}
    assert client.put('/api/savings-goals/' + goal, headers=bob, json=updated).status_code == 404
    assert client.put('/api/savings-goals/' + goal, headers=alice, json=updated).status_code == 200
    row = client.get('/api/savings-goals', headers=alice).json()['items'][0]
    assert (row['label'], row['target_vnd']) == ('New trip', 3000000)
    assert client.put('/api/savings-goals/' + goal, headers=alice, json={**body, 'target_date': '2030-02-31'}).status_code == 422
    assert client.put('/api/savings-goals/' + goal, headers=alice, json={**body, 'savings_id': 'not-owned'}).status_code == 404
    assert client.post('/api/savings-goals', headers=alice, json={**body, 'label': '  '}).status_code == 422


def test_saved_recipient_uses_vietqr_catalog_but_name_is_explicitly_simulated(client, alice, monkeypatch):
    monkeypatch.setattr(vietqr, '_banks', [{'bin': '970436', 'code': 'VCB', 'shortName': 'Vietcombank'}])
    response = client.post('/api/customer/beneficiaries', headers=alice,
                           json={'bank': '970436', 'account_id': '001234567890', 'nickname': 'Demo VCB'})
    assert response.status_code == 201, response.text
    row = response.json()
    assert row['bank'] == 'Vietcombank' and row['account_id'] == '001234567890'
    assert row['holder_name'].startswith('SIMULATED RECIPIENT')
    bad = client.post('/api/customer/beneficiaries/lookup', headers=alice, json={'bank': 'unknown', 'account_id': '001234567890'})
    assert bad.status_code == 422


def test_ticket_status_filter_is_applied_before_pagination_and_owner_scope(client, alice, bob):
    from .conftest import sign_in
    body = {'subject': 'Explore support', 'description': 'Please check the demo.'}
    first = client.post('/api/support/tickets', headers=alice, json=body).json()['id']
    client.post('/api/support/tickets', headers=alice, json={**body, 'subject': 'Other open request'})
    client.post('/api/support/tickets', headers=bob, json=body)
    staff = sign_in(client, 'support', 'Support@2026')
    client.patch('/api/support/tickets/' + first, headers=staff, json={'status': 'RESOLVED'})
    result = client.get('/api/support/tickets?status=RESOLVED&limit=1', headers=alice).json()
    assert result['total'] == 1 and result['items'][0]['id'] == first
    assert client.get('/api/support/tickets?status=RESOLVED', headers=bob).json()['total'] == 0
    assert client.get('/api/support/tickets?status=INVALID', headers=alice).status_code == 422
