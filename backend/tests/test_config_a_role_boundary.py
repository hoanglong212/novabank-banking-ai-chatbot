"""Fix round 1, step 1: config A drops the prompt-injection layers, never the app's own role checks."""
import jwt
import pytest
from app import auth, staff_tools
from app.agent.agent_access import AUDIENCE, MODELS
from tests.acceptance_helpers import client, login
from tests.test_week7 import grant_for


def configure(client, config, users=('alice', 'support', 'operations')):
    response = client.put('/api/admin/agent-gateway', headers=login(client, 'admin'), json={'config': config, 'users': list(users)})
    assert response.status_code == 200, response.text


def call(client, token, name, args):
    return client.post('/api/agent/tools', headers=token, json={'name': name, 'arguments': args}).json()


def token_tools(grant):
    return set(jwt.decode(grant['delegated_token'], auth.SECRET, algorithms=['HS256'], audience=AUDIENCE)['tools'])


def test_customer_at_a_gets_no_staff_tools_and_is_role_checked(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    configure(client, 'A')
    _, grant, token = grant_for(client, login(client), 'What is my balance?')
    assert client.get('/api/agent/context', headers=token).json()['gateway'] == 'off'
    assert token_tools(grant) == set(MODELS) - set(staff_tools.PERMISSIONS)
    for name, args in (('list_tickets', {}), ('get_customer_summary', {'user_id': 'bob'})):
        result = call(client, token, name, args)
        assert (result['decision'], result['reason']) == ('DENY', 'ROLE_NOT_PERMITTED'), (name, result)


@pytest.mark.parametrize('who,content,name', [('support', 'List the open tickets.', 'list_tickets'),
                                              ('operations', 'List the customers.', 'list_customers')])
def test_staff_at_a_keep_their_own_role_tools(client, monkeypatch, who, content, name):
    monkeypatch.setenv('ENV', 'demo')
    configure(client, 'A')
    _, _, token = grant_for(client, login(client, who), content)
    assert call(client, token, name, {})['decision'] == 'ALLOW'


@pytest.mark.parametrize('config', ['B', 'C', 'D'])
def test_b_c_d_role_boundary_is_unchanged(client, monkeypatch, config):
    monkeypatch.setenv('ENV', 'demo')
    configure(client, config)
    _, grant, token = grant_for(client, login(client), 'What is my balance?')
    assert not token_tools(grant) & set(staff_tools.PERMISSIONS)
    assert call(client, token, 'list_tickets', {})['reason'] == 'ROLE_NOT_PERMITTED'
    _, _, staff = grant_for(client, login(client, 'support'), 'List the open tickets.')
    assert call(client, staff, 'list_tickets', {})['decision'] == 'ALLOW'
