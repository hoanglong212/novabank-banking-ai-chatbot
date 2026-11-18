import json
from pathlib import Path
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for

CASES = Path(__file__).resolve().parents[2] / 'research/cases/mentor-2026-11-14'


@pytest.mark.parametrize('path', sorted(CASES.glob('*.json')), ids=lambda p: p.stem)
def test_mentor_goal_reconstruction_is_denied_with_legitimate_read_control(client, path):
    case = json.loads(path.read_text(encoding='utf-8'))
    who = login(client)
    with get_db().connect() as conn:
        before = tuple(conn.execute('SELECT (SELECT COUNT(*) FROM users),(SELECT COUNT(*) FROM accounts),(SELECT SUM(balance_vnd) FROM accounts)').fetchone())
    cid, _, token = run_for(client, who, case['turns'][-1])
    for content in case['turns'][:-1]:
        get_db().append_message(cid, 'user', content)
    result = client.post('/api/agent/tools', headers=token, json={'name': case['tool'], 'arguments': case['arguments']})
    assert result.status_code == 200, result.text
    assert result.json()['decision'] == case['expected']
    with get_db().connect() as conn:
        after = tuple(conn.execute('SELECT (SELECT COUNT(*) FROM users),(SELECT COUNT(*) FROM accounts),(SELECT SUM(balance_vnd) FROM accounts)').fetchone())
    assert before == after
    if case['tool'] == 'prepare_transfer':
        control_args = {**case['arguments'], 'to_account': 'ACC-BOB-001'}
        assert client.get('/api/agent/context', headers=token).status_code == 401
        _, _, control_token = run_for(client, who, case['turns'][-1])
        approved = client.post('/api/agent/tools', headers=control_token, json={'name': 'prepare_transfer', 'arguments': control_args})
        assert approved.status_code == 200 and approved.json()['decision'] == 'ALLOW'
    # Positive control: the customer still reads their own balance through the gateway.
    _, _, own = run_for(client, who, 'What is my account balance?')
    control = client.post('/api/agent/tools', headers=own, json={'name': 'get_account_balance', 'arguments': {}})
    assert control.status_code == 200 and control.json()['decision'] == 'ALLOW'
