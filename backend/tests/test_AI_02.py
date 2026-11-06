from tests.acceptance_helpers import *


def test_AI_02_filtered_tool_returns_only_matching_owned_transactions(client):
    who = login(client); payment = pay(client, who, 2345)
    draft = client.post('/api/transfers', headers=who, json={'to_account':'ACC-CHARLIE-001','amount_vnd':3456}).json()
    assert client.post('/api/transfers/'+draft['id']+'/confirm', headers=who, json={'otp':transfer_code(draft)}).status_code == 200
    cid = client.post('/api/conversations', headers=who, json={'title':'Filter transactions'}).json()['id']
    run = client.post('/api/agent/runs', headers=who, json={'conversation_id':cid,'content':'Show transactions to Bob today','profile':'baseline'}).json()
    token = {'Authorization':'Bearer '+run['delegated_token']}
    today = date.today().isoformat()
    def call(args):
        return client.post('/api/agent/tools', headers=token, json={'name':'get_recent_transactions','arguments':args}).json()
    result = call({'from_date':today,'to_date':today,'recipient':'BOB','limit':20})
    assert result['decision'] == 'ALLOW', result
    assert [r['id'] for r in result['result']['items']] == [payment['transaction_id']]
    assert call({'from_date':'2000-01-01','to_date':'2000-01-02','recipient':'Bob'})['result']['items'] == []
    assert call({'recipient':"%' OR 1=1--"})['result']['items'] == []
    assert call({'from_date':'2026-12-31','to_date':'2026-01-01'})['decision'] == 'DENY'

def test_AI_02_transaction_tool_supports_period_and_recipient_filters(client):
    from app.agent_access import tool_schemas
    candidates=[tool['function'] for tool in tool_schemas() if 'transaction' in tool['function']['name']]
    supported=[]
    for tool in candidates:
        fields=set(tool['parameters'].get('properties',{}))
        supported.append({'name':tool['name'],'fields':sorted(fields)})
        if fields.intersection({'from_date','date_from'}) and fields.intersection({'counterparty','recipient','to_account'}):
            return
    assert False, f'No transaction tool supports date and recipient filters: {supported}'



from tests.conftest import transfer_code
