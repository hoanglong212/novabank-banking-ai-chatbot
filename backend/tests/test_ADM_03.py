from tests.acceptance_helpers import *

def test_ADM_03_fee_locked_at_draft_creation_limits_rechecked_at_confirm(client):
    who=login(client)
    draft=client.post('/api/transfers',headers=who,json={'to_account':'ACC-BOB-001','amount_vnd':2000}).json()
    admin = login(client, 'admin')
    assert client.patch('/api/admin/settings',headers=admin,json={'transfer_fee_vnd':1000}).status_code==200
    result=client.post('/api/transfers/'+draft['id']+'/confirm',headers=who,json={'otp':transfer_code(draft)})
    assert result.status_code==200
    with get_db().connect() as conn:
        fee=conn.execute('SELECT fee_vnd FROM transfer_quotes WHERE transfer_id=?',(draft['id'],)).fetchone()[0]
    assert fee == 0  # User decision: quote is locked at creation, not confirmation.
    draft = client.post('/api/transfers', headers=who, json={'to_account':'ACC-BOB-001','amount_vnd':2000}).json()
    assert draft['fee_vnd'] == 1000
    assert client.patch('/api/admin/settings', headers=admin, json={'transfer_limit_vnd':1000}).status_code == 200
    before = client.get('/api/me', headers=who).json()['accounts']
    response = client.post('/api/transfers/'+draft['id']+'/confirm', headers=who, json={'otp':transfer_code(draft)})
    assert response.status_code in (400,409)
    assert client.get('/api/me', headers=who).json()['accounts'] == before



from tests.conftest import transfer_code
