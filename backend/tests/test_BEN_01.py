from tests.acceptance_helpers import *

def test_BEN_01_edit_saved_nickname(client):
    who=login(client); saved=beneficiary(client,who)
    response=client.patch('/api/customer/beneficiaries/'+saved['id'],headers=who,json={'nickname':'Rent'})
    assert response.status_code==200, f'Editing saved recipient returned {response.status_code}; expected 200'
    row = client.get('/api/customer/beneficiaries', headers=who).json()['items'][0]
    assert row['nickname'] == 'Rent' and row['account_id'] == 'ACC-BOB-001'
    other = login(client, 'bob')
    assert client.patch('/api/customer/beneficiaries/'+saved['id'], headers=other, json={'nickname':'Stolen'}).status_code == 404
    assert client.patch('/api/customer/beneficiaries/'+saved['id'], headers=who, json={'nickname':'  '}).status_code == 422
    assert client.patch('/api/customer/beneficiaries/'+saved['id'], headers=who, json={'nickname':'Rent','account_id':'ACC-CHARLIE-001'}).status_code == 422


def test_BEN_01_search_saved_recipients(client):
    who=login(client); beneficiary(client,who); beneficiary(client,who,'ACC-CHARLIE-001','Work')
    rows=client.get('/api/customer/beneficiaries?q=Family',headers=who).json()['items']
    assert len(rows)==1 and rows[0]['nickname']=='Family', f'Search returned {len(rows)} rows; expected one matching recipient'
    assert client.get('/api/customer/beneficiaries', headers=who, params={'q':"%' OR 1=1--"}).json()['items'] == []


