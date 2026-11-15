import os
from tests.acceptance_helpers import *


def test_legacy_environment_flag_cannot_enable_routes_without_active_pytest(client, monkeypatch):
    who = login(client)
    cid = client.post('/api/conversations', headers=who, json={'title': 'Legacy confinement'}).json()['id']
    monkeypatch.setenv('LEGACY_AGENT_TEST_MODE', 'true')
    active_test = os.environ['PYTEST_CURRENT_TEST']
    monkeypatch.delenv('PYTEST_CURRENT_TEST')
    path = '/api/conversations/' + cid
    assert client.post(path + '/messages', headers=who, json={'content': 'What is my balance?'}).status_code == 404
    assert client.post(path + '/demo/tool-check', headers=who, json={'tool_name': 'get_account_balance', 'arguments': {}}).status_code == 404
    assert client.get('/api/health').json()['agent_mode'] == 'service'
    # Positive control: explicitly enabled legacy regression remains available inside pytest.
    monkeypatch.setenv('PYTEST_CURRENT_TEST', active_test)
    assert client.post(path + '/messages', headers=who, json={'content': 'What is my balance?'}).status_code == 200
    assert client.post(path + '/demo/tool-check', headers=who, json={'tool_name': 'get_account_balance', 'arguments': {}}).status_code == 200
