from app.main import get_db
from .conftest import new_chat


def new_run(client, alice):
    cid = new_chat(client, alice)
    r = client.post('/api/agent/runs', headers=alice, json={'conversation_id': cid, 'content': 'What is my balance?', 'profile': 'defended'})
    assert r.status_code == 201, r.text
    return r.json()


def test_delegated_token_cannot_confirm_or_cross_owner(client, alice, bob):
    run = new_run(client, alice)
    token = {'Authorization': 'Bearer ' + run['delegated_token']}
    assert client.get('/api/agent/context', headers=token).status_code == 200
    assert client.get('/api/me', headers=token).status_code == 401
    assert client.post('/api/actions/confirm', headers=token, json={'challenge_id': 'a' * 43, 'code': '123456'}).status_code == 401
    r = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {'account_id': 'ACC-BOB-001'}})
    assert r.status_code == 200 and r.json()['decision'] == 'DENY', r.text
    assert '8750000' not in r.text
    assert client.get('/api/agent/runs/' + run['run_id'], headers=bob).status_code == 404
    client.post('/api/auth/logout', headers=alice)
    assert client.get('/api/agent/context', headers=token).status_code == 401


def test_unrequested_write_denied_and_requested_ticket_needs_approval(client, alice, bob):
    run = new_run(client, alice)
    token = {'Authorization': 'Bearer ' + run['delegated_token']}
    r = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_support_ticket', 'arguments': {'subject': 'Fake', 'description': 'unrequested write'}})
    assert r.json()['decision'] == 'DENY'
    cid = new_chat(client, alice)
    run = client.post('/api/agent/runs', headers=alice, json={'conversation_id': cid, 'content': 'Create a support ticket: my card is blocked', 'profile': 'defended'}).json()
    token = {'Authorization': 'Bearer ' + run['delegated_token']}
    r = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_support_ticket', 'arguments': {'subject': 'Card', 'description': 'My card is blocked'}})
    assert r.json()['decision'] == 'ALLOW', r.text
    approval = r.json()['result']['approval_id']
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM support_tickets WHERE subject='Card'").fetchone()[0] == 0
    assert client.post('/api/agent/approvals/' + approval, headers=bob, json={'approve': True}).status_code == 404
    r = client.post('/api/agent/approvals/' + approval, headers=alice, json={'approve': True})
    assert r.status_code == 200, r.text
    assert client.post('/api/agent/approvals/' + approval, headers=alice, json={'approve': True}).json() == r.json()


def test_agent_only_receives_approved_knowledge_and_bounded_trace(client, alice):
    run = new_run(client, alice); token = {'Authorization': 'Bearer ' + run['delegated_token']}
    for _ in range(8):
        r = client.post('/api/agent/tools', headers=token, json={'name': 'get_accounts', 'arguments': {}})
        assert r.status_code == 200
    r = client.post('/api/agent/tools', headers=token, json={'name': 'get_accounts', 'arguments': {}})
    assert r.status_code == 429
    trace = client.get('/api/agent/runs/' + run['run_id'], headers=alice).json()
    assert len(trace['tool_calls']) == 8
    assert 'delegated_token' not in trace
