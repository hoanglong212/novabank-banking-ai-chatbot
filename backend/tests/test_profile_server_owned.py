"""R2: the server, not the client, picks the defence profile (BAO-CAO-KIEM-TRA-TUAN-7.md, R2)."""
import pytest
from tests.acceptance_helpers import *


def run_profile(client, who, requested):
    cid = client.post('/api/conversations', headers=who, json={'title': 'profile'}).json()['id']
    grant = client.post('/api/agent/runs', headers=who, json={'conversation_id': cid, 'content': 'What is my balance?', 'profile': requested})
    assert grant.status_code == 201, grant.text
    stored = client.get('/api/agent/runs/' + grant.json()['run_id'], headers=who).json()['profile']
    assert stored == grant.json()['profile']
    return stored


@pytest.mark.parametrize('environment,role,expected', [
    ('', 'alice', 'defended'), ('demo', 'alice', 'defended'), ('lab', 'alice', 'defended'),
    ('', 'admin', 'defended'), ('production', 'admin', 'defended'),
    ('demo', 'support', 'defended'), ('demo', 'operations', 'defended'),
    ('demo', 'admin', 'baseline'), ('lab', 'admin', 'baseline'),
])
def test_baseline_only_for_admin_in_lab(client, monkeypatch, environment, role, expected):
    monkeypatch.setenv('ENV', environment)
    assert run_profile(client, login(client, role), 'baseline') == expected


def test_defended_is_never_downgraded(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    assert run_profile(client, login(client, 'admin'), 'defended') == 'defended'


def test_customer_asking_for_baseline_keeps_the_two_denial_stop(client):
    who = login(client)
    cid = client.post('/api/conversations', headers=who, json={'title': 'profile'}).json()['id']
    grant = client.post('/api/agent/runs', headers=who, json={'conversation_id': cid, 'content': 'What is my balance?', 'profile': 'baseline'}).json()
    token = {'Authorization': 'Bearer ' + grant['delegated_token']}
    for _ in range(2):
        denied = client.post('/api/agent/tools', headers=token, json={'name': 'list_customers', 'arguments': {}}).json()
        assert denied['decision'] == 'DENY'
    assert denied['halt'] is True
    assert client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {}}).status_code == 429
