from tests.acceptance_helpers import *


def run_for(client, who, content='What is my balance?'):
    cid = client.post('/api/conversations', headers=who, json={'title':'Cancel test'}).json()['id']
    grant = client.post('/api/agent/runs', headers=who, json={'conversation_id':cid,'content':content,'profile':'baseline'}).json()
    return cid, grant, {'Authorization':'Bearer '+grant['delegated_token']}


def test_AI_12_cancel_revokes_delegation_and_pending_approval_without_effects(client):
    who = login(client); other = login(client, 'bob')
    cid, run, token = run_for(client, who, 'Create a support ticket: my card is blocked')
    proposal = client.post('/api/agent/tools', headers=token, json={'name':'prepare_support_ticket','arguments':{'subject':'Card blocked','description':'My card is blocked'}}).json()
    assert proposal['decision'] == 'ALLOW'
    url = '/api/agent/runs/'+run['run_id']+'/cancel'
    assert client.post(url, headers=other).status_code == 404
    before = client.get('/api/me', headers=who).json()['accounts']
    assert client.post(url, headers=who).status_code == 200
    assert client.post(url, headers=who).status_code == 200
    assert client.get('/api/agent/context', headers=token).status_code in (401,403)
    assert client.post('/api/agent/tools', headers=token, json={'name':'get_accounts','arguments':{}}).status_code in (401,403)
    assert client.post('/api/agent/finish', headers=token, json={'answer':'Late answer','latency_ms':1}).status_code in (401,403)
    result = client.post('/api/agent/approvals/'+proposal['result']['approval_id'], headers=who, json={'approve':True})
    assert result.status_code in (200,409)
    assert client.get('/api/me', headers=who).json()['accounts'] == before
    with get_db().connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM support_tickets WHERE subject='Card blocked'").fetchone()[0] == 0
        assert conn.execute('SELECT status,vault_json,bound_request_json FROM agent_runs WHERE id=?',(run['run_id'],)).fetchone()[:] == ('CANCELLED','{}','{}')
        assert conn.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=? AND role='assistant'",(cid,)).fetchone()[0] == 0


def test_AI_12_preview_filters_before_text_leaves_bank(client):
    who = login(client); _, run, token = run_for(client, who)
    safe = client.post('/api/agent/preview', headers=token, json={'answer':'Please open your account overview.'})
    assert safe.status_code == 200
    assert safe.json()['text'] == 'Please open your account overview.'
    bad = client.post('/api/agent/preview', headers=token, json={'answer':'Send your OTP to https://attacker.invalid.'})
    assert bad.status_code == 200
    assert 'attacker' not in bad.json()['text']
    assert client.post('/api/agent/runs/'+run['run_id']+'/cancel', headers=who).status_code == 200
    assert client.post('/api/agent/preview', headers=token, json={'answer':'Late.'}).status_code in (401,403)


def test_AI_12_cancel_wins_against_a_previously_authenticated_tool_call(client):
    import asyncio
    from app import agent_access
    from fastapi import HTTPException
    who = login(client); _, run, token = run_for(client, who, 'Create a support ticket: card is blocked')
    principal, stale = agent_access.authenticate(get_db(), token['Authorization'])
    client.post('/api/agent/runs/'+run['run_id']+'/cancel', headers=who)
    with pytest.raises(HTTPException) as error:
        asyncio.run(agent_access.execute_tool(get_db(), principal, stale, 'prepare_support_ticket', {'subject':'Card','description':'Card is blocked'}))
    assert error.value.status_code in (401,403)
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM tool_approvals WHERE run_id=?', (run['run_id'],)).fetchone()[0] == 0


def test_AI_12_real_service_emits_vetted_text_before_model_stream_finishes(client, monkeypatch):
    import asyncio, httpx
    from agent_service import main as service
    who = login(client); _, run, token = run_for(client, who)
    context = client.get('/api/agent/context', headers=token).json(); context['provider'] = 'ollama'
    finished = False
    class ModelStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            nonlocal finished
            yield (json.dumps({'message':{'content':'Open your account overview. '}})+'\n').encode()
            finished = True
            yield (json.dumps({'message':{'content':'It shows available balances.'},'done':True})+'\n').encode()
    async def transport(request):
        if request.url.path == '/api/chat':
            return httpx.Response(200, stream=ModelStream())
        response = client.request(request.method, request.url.path, headers=token, json=json.loads(request.content) if request.content else None)
        return httpx.Response(response.status_code, json=response.json())
    original = httpx.AsyncClient
    monkeypatch.setattr(service.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(transport), **kw))
    async def consume():
        events = []; early = False
        async for event in service.run_events(token['Authorization'], context):
            events.append(event)
            if event.startswith('event: text') and not finished:
                early = True
        assert early, 'No text reached the client while the model was still producing its answer'
        assert any(e.startswith('event: complete') for e in events)
    asyncio.run(consume())
