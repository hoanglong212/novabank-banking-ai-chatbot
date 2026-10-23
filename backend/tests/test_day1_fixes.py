import asyncio
import json
import sqlite3

import httpx
import pytest

from app.auth import DEMO_USERS
from app.database import Database
from app.gateway import PolicyGateway
from app.tools import OLLAMA_TOOLS, TOOL_MODELS, ToolDispatcher
from .conftest import new_chat


def test_connection_closed_after_commit_and_rollback(tmp_path):
    db = Database(str(tmp_path / 'closed.sqlite3'))
    with db.connect() as conn:
        conn.execute('CREATE TABLE example (value INTEGER)')
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute('SELECT 1')
    with pytest.raises(RuntimeError):
        with db.connect() as failed:
            failed.execute('INSERT INTO example VALUES (1)')
            raise RuntimeError('rollback')
    with pytest.raises(sqlite3.ProgrammingError):
        failed.execute('SELECT 1')
    with db.connect() as check:
        assert check.execute('SELECT COUNT(*) FROM example').fetchone()[0] == 0


def test_ticket_absent_and_dispatcher_rejects_write(tmp_path):
    assert 'create_support_ticket' not in TOOL_MODELS
    assert all(t['function']['name'] != 'create_support_ticket' for t in OLLAMA_TOOLS)
    db = Database(str(tmp_path / 'readonly.sqlite3'))
    db.initialize()
    cid = db.create_conversation('alice', 'Read only')['id']
    result = asyncio.run(ToolDispatcher(db, PolicyGateway(mode='local')).run(
        DEMO_USERS[0], cid, 'create_support_ticket', {'subject':'Ticket','description':'Do not create this'}))
    assert result['error'] == 'TOOL_DENIED'
    assert db.ticket_count('alice') == 0


def test_ollama_readonly_and_keep_alive(client, alice, monkeypatch):
    import app.agent as agent
    from app.main import get_db
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    monkeypatch.setenv('OLLAMA_KEEP_ALIVE', '60m')
    original = httpx.AsyncClient
    def transport(request):
        body = json.loads(request.content)
        assert body['keep_alive'] == '60m'
        assert all(t['function']['name'] != 'create_support_ticket' for t in body['tools'])
        return httpx.Response(200, json={'message': {'role':'assistant', 'content':'', 'tool_calls':[
            {'function':{'name':'create_support_ticket','arguments':{'subject':'Ticket','description':'Unwanted write'}}}]}})
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda *a, **kw: original(transport=httpx.MockTransport(transport)))
    cid = new_chat(client, alice)
    result = client.post(f'/api/conversations/{cid}/messages', headers=alice,
                         json={'content':'Create a support ticket about my delayed transfer'})
    assert result.status_code == 200
    assert 'read-only' in result.json()['message']['content']
    assert get_db().ticket_count('alice') == 0
    assert not any(e['executed'] for e in result.json()['tool_events'])
