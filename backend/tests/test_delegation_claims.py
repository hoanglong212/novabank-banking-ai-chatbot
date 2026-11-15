import json
import jwt
from app import auth
from app.agent import agent_access
from app.auth_crypto import encrypt_secret
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


def test_claims_are_required_and_independent_of_live_tool_catalog(client, monkeypatch):
    who = login(client)
    _, grant, token = run_for(client, who)
    claims = jwt.decode(grant['delegated_token'], auth.SECRET, algorithms=['HS256'], audience=agent_access.AUDIENCE)
    assert claims['role'] == 'customer'
    assert 'get_account_balance' in claims['tools'] and len(claims['intent']) == 64
    for key in ('tools', 'intent', 'role'):
        broken = {k: v for k, v in claims.items() if k != key}
        bad = {'Authorization': 'Bearer ' + jwt.encode(broken, auth.SECRET, algorithm='HS256')}
        assert client.get('/api/agent/context', headers=bad).status_code == 401
    # Catalog expands after issuance; the signed capability must not expand with it.
    original = agent_access.permitted_tools
    monkeypatch.setattr(agent_access, 'permitted_tools', lambda intent, role: original(intent, role) | {'prepare_transfer'})
    denied = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}}).json()
    assert denied['decision'] == 'DENY' and denied['reason'] == 'TOOL_NOT_IN_TOKEN'
    control = client.post('/api/agent/tools', headers=token, json={'name': 'get_account_balance', 'arguments': {}}).json()
    assert control['decision'] == 'ALLOW'


def test_intent_hash_mismatch_blocks_proposal_but_unchanged_intent_allows(client):
    who = login(client)
    text = 'Transfer 10000 VND to ACC-BOB-001 content lunch'
    _, grant, token = run_for(client, who, text)
    with get_db().connect() as conn:
        conn.execute('UPDATE agent_runs SET bound_request_json=? WHERE id=?', (encrypt_secret(get_db(), json.dumps({'text': text, 'tool': 'create_transfer', 'arguments': {'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 10000}})), grant['run_id']))
    response = client.post('/api/agent/tools', headers=token, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 10000}})
    assert response.status_code == 200
    assert response.json()['reason'] == 'INTENT_HASH_MISMATCH'
    _, _, fresh = run_for(client, who, text)
    control = client.post('/api/agent/tools', headers=fresh, json={'name': 'prepare_transfer', 'arguments': {'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'lunch'}}).json()
    assert control['decision'] == 'ALLOW'
