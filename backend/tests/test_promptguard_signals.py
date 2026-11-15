"""Exercise bank-owned signal events and ablation switches through the API."""
import json

import pytest

from app.agent import agent_guard, promptguard
from tests.acceptance_helpers import client, get_db, login
from tests.test_AI_12 import run_for


@pytest.mark.parametrize('config', ['A', 'B', 'C', 'D'])
def test_source_classifier_emits_each_visited_stage_only_in_b_and_d(client, monkeypatch, config):
    monkeypatch.setenv('ENV', 'lab')
    admin, who = login(client, 'admin'), login(client)
    changed = client.put('/api/admin/agent-gateway', headers=admin,
                         json={'config': config, 'users': ['alice'], 'minutes': 2})
    assert changed.status_code == 200
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    async def pg(text):
        return {'injection': False, 'available': True, 'method': 'prompt_guard_2', 'score': 0.001}
    async def judge(text):
        return {'injection': False, 'method': 'local_model'}
    monkeypatch.setattr(promptguard, 'classify', pg)
    monkeypatch.setattr(agent_guard, 'classify', judge)
    _, grant, delegated = run_for(client, who, 'Show my recent transactions.')
    response = client.post('/api/agent/tools', headers=delegated,
                           json={'name': 'get_recent_transactions', 'arguments': {}})
    assert response.status_code == 200 and response.json()['decision'] == 'ALLOW'
    with get_db().connect() as conn:
        stages = [json.loads(row[0])['stage'] for row in conn.execute(
            "SELECT detail_json FROM security_events WHERE run_id=? AND event='classifier_signal' ORDER BY rowid",
            (grant['run_id'],))]
    assert stages == (['regex', 'prompt_guard_2', 'qwen'] if config in ('B', 'D') else [])
