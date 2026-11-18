import json
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_ticket_task_has_no_account_write_tool_and_only_enums_reach_main_model(client):
    customer = login(client)
    ticket = client.post('/api/support/tickets', headers=customer, json={'subject': 'Secret freeform phrase', 'description': 'My card payment needs checking, please help.'}).json()
    admin = login(client, 'admin')
    _, grant, token = run_for(client, admin, 'Reply to ' + ticket['id'])
    context = client.get('/api/agent/context', headers=token).json()
    names = {tool['function']['name'] for tool in context['tools']}
    assert 'propose_ticket_reply' in names and 'propose_account_status' not in names
    response = client.post('/api/agent/tools', headers=token, json={'name': 'read_ticket', 'arguments': {'ticket_id': ticket['id']}}).json()
    assert response['decision'] == 'ALLOW'
    encoded = json.dumps(response['result'])
    assert 'Secret freeform phrase' not in encoded and 'description' not in encoded and 'summary' not in encoded
    assert response['result']['category'] in ('GENERAL', 'CARD')
    trace = client.get('/api/agent/runs/' + grant['run_id'], headers=admin).json()
    assert trace['human_assessments'][0]['assessment']['summary']
    assert 'Secret freeform phrase' in client.get('/api/support/tickets/' + ticket['id'], headers=admin).text
    assert client.get('/api/agent/runs/' + grant['run_id'], headers=customer).status_code == 404
