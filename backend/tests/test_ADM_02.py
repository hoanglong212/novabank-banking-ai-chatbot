from tests.acceptance_helpers import *


def test_ADM_02_customer_status_audit_retains_old_and_new_state(client):
    who = login(client, 'admin')
    assert client.patch('/api/admin/users/alice', headers=who, json={'status':'DISABLED','kyc_status':'VERIFIED'}).status_code == 200
    event = next(r for r in client.get('/api/admin/audit', headers=who).json()['items'] if r['action']=='CUSTOMER_UPDATED')
    change = json.loads(event['reason_code'])
    assert change['before'] == {'status':'ACTIVE','kyc_status':'UNVERIFIED'}
    assert change['after'] == {'status':'DISABLED','kyc_status':'VERIFIED'}

def test_ADM_02_audit_contains_before_and_after(client):
    who=login(client,'admin')
    assert client.patch('/api/admin/accounts/ACC-ALICE-001',headers=who,json={'status':'FROZEN'}).status_code==200
    rows=client.get('/api/admin/audit',headers=who).json()['items']
    event=next(row for row in rows if row['action']=='ACCOUNT_STATUS')
    text=json.dumps(event)
    assert 'ACTIVE' in text and 'FROZEN' in text, 'Account audit stores the resulting state but omits the previous state'


def test_ADM_02_setting_audit_has_actor_resource_and_old_new_values(client):
    who = login(client, 'admin')
    assert client.patch('/api/admin/settings', headers=who, json={'transfer_fee_vnd':1000}).status_code == 200
    event = next(r for r in client.get('/api/admin/audit', headers=who).json()['items'] if r['action'] == 'SETTING_UPDATED')
    assert event['owner_id'] == 'admin' and event['resource_id'] == 'transfer_fee_vnd' and event['created_at']
    change = json.loads(event['reason_code'])
    assert change == {'before': 0, 'after': 1000}


