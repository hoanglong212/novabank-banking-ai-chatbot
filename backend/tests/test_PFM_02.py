from tests.acceptance_helpers import *


@pytest.mark.parametrize('kind', ['PAY_BILL', 'CARD_PURCHASE', 'INTERBANK'])
def test_PFM_02_all_spending_posting_paths_notify_without_insights_read(client, kind):
    from tests.test_customer_products import confirm
    from app.posting import business_day
    from app.database import now
    who = login(client)
    month = business_day(now())[:7]
    category = 'transfer' if kind == 'INTERBANK' else 'food'
    if kind == 'PAY_BILL':
        bill = client.get('/api/products/bills', headers=who).json()['items'][0]
        category = bill['category']
        payload = {'kind':kind, 'resource_id':bill['id'], 'account_id':'ACC-ALICE-001'}
    elif kind == 'CARD_PURCHASE':
        card = next(r for r in client.get('/api/products/cards', headers=who).json()['items'] if r['kind']=='CREDIT')
        payload = {'kind':kind,'resource_id':card['id'],'amount_vnd':2000,'label':'food'}
    assert client.put('/api/insights/budgets', headers=who, json={'month':month,'category':category,'amount_vnd':1000}).status_code == 200
    if kind == 'INTERBANK':
        draft = client.post('/api/transfers', headers=who, json={'to_bank':'Demo Bank A','to_account':'123456789','to_name':'Test','amount_vnd':2000}).json()
        assert client.post('/api/transfers/'+draft['id']+'/confirm', headers=who, json={'otp':transfer_code(draft)}).status_code == 200
        assert not any(r['kind']=='BUDGET' for r in client.get('/api/notifications',headers=who).json()['items'])
        from app.settlement import process_due
        process_due(get_db(), force=True)
    else:
        draft = client.post('/api/products/actions', headers=who, json=payload)
        assert draft.status_code == 202
        assert confirm(client, who, draft.json(), 'budget-posting').status_code == 200
    assert sum(r['kind']=='BUDGET' for r in client.get('/api/notifications',headers=who).json()['items']) == 1

def test_PFM_02_budget_alert_created_by_crossing_threshold(client):
    who=login(client); month=date.today().strftime('%Y-%m')
    assert client.put('/api/insights/budgets',headers=who,json={'month':month,'category':'transfer','amount_vnd':1000}).status_code==200
    pay(client,who)
    rows=client.get('/api/notifications',headers=who).json()['items']
    immediate=sum(row['kind']=='BUDGET' for row in rows)
    client.get('/api/insights',headers=who,params={'month':month})
    after_read=sum(row['kind']=='BUDGET' for row in client.get('/api/notifications',headers=who).json()['items'])
    assert immediate==1, f'Alerts after payment={immediate}, after opening insights={after_read}; expected alert immediately after crossing budget'
    pay(client, who)
    assert sum(r['kind']=='BUDGET' for r in client.get('/api/notifications',headers=who).json()['items']) == 1
    assert not any(r['kind']=='BUDGET' for r in client.get('/api/notifications',headers=login(client,'bob')).json()['items'])



from tests.conftest import transfer_code
