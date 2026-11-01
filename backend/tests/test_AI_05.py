from tests.acceptance_helpers import *
from tests.agent_acceptance_helpers import run_for


@pytest.mark.parametrize('arguments', [
    {'to_account':'ACC-BOB-001','amount_vnd':-1000},
    {'to_account':'ACC-BOB-001','amount_vnd':'1000'},
    {'to_account':'ACC-BOB-001'},
    {'to_account':'ACC-BOB-001','amount_vnd':True},
    {'to_account':'ACC-BOB-001','amount_vnd':1000,'owner_id':'bob'},
])
def test_AI_05_invalid_tool_schema_cannot_create_a_proposal(client, arguments):
    who = login(client)
    _, grant, token = run_for(client, who, 'Transfer 1000 VND to ACC-BOB-001')
    before = client.get('/api/me', headers=who).json()['accounts']
    response = client.post('/api/agent/tools', headers=token, json={'name':'prepare_transfer','arguments':arguments})
    assert response.status_code == 200
    assert response.json()['decision'] == 'DENY'
    assert response.json()['reason'] == 'INVALID_ARGUMENTS'
    assert response.json()['result']['error']
    assert 'arguments' in response.json()['result'].get('message','').lower()
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM tool_approvals WHERE run_id=?', (grant['run_id'],)).fetchone()[0] == 0
    assert client.get('/api/me', headers=who).json()['accounts'] == before
