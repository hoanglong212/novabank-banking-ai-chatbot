from tests.acceptance_helpers import *
from tests.agent_acceptance_helpers import run_for, exercise, calls


@pytest.mark.parametrize('kind,changes,responses,delay,rounds,tools,reason', [
    ('round', {}, [calls(('get_accounts',{}))], 0, 4, 4, 'ROUND_LIMIT'),
    ('tool', {}, [calls(*[('get_accounts',{})]*9)], 0, 1, 8, 'TOOL_LIMIT'),
    ('time', {'timeout_seconds':0.01}, [{'content':'Late answer'}], 0.1, 1, 0, 'TIME_LIMIT'),
])
def test_AI_10_exact_limits_stop_and_persist_reason(client, monkeypatch, kind, changes, responses, delay, rounds, tools, reason):
    who = login(client); _, grant, token = run_for(client, who)
    payloads, requests, events = exercise(client, monkeypatch, token, responses, changes, delay)
    assert len(payloads) == rounds
    assert sum(path == '/api/agent/tools' for path, _ in requests) == tools
    detail = client.get('/api/agent/runs/'+grant['run_id'], headers=who).json()
    assert detail['status'] == 'FAILED'
    assert detail.get('termination_reason') == reason
    assert len(detail['tool_calls']) == tools
    assert any(e.startswith('event: complete') for e in events)
