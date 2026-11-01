from datetime import datetime, timezone
import json
from typing import Literal
import time
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import Field
from . import agent_access
from .auth_crypto import decrypt_secret
from .config import setting
from .database import now
from .dependencies import customer_user, get_db
from .guard import inspect_prompt
from .identity import transaction
from .identity_schemas import IdentityInput

router = APIRouter(prefix='/api')


class RunInput(IdentityInput):
    conversation_id: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=4000)
    profile: Literal['baseline', 'defended'] = 'defended'


class ToolInput(IdentityInput):
    name: str = Field(min_length=1, max_length=80)
    arguments: dict = Field(default_factory=dict)


class FinishInput(IdentityInput):
    answer: str = Field(max_length=24000)
    input_tokens: int = Field(default=0, ge=0, le=1000000)
    output_tokens: int = Field(default=0, ge=0, le=1000000)
    latency_ms: int = Field(ge=0, le=300000)
    status: Literal['COMPLETED', 'FAILED'] = 'COMPLETED'


class PreviewInput(IdentityInput):
    answer: str = Field(max_length=24000)


class ApprovalInput(IdentityInput):
    approve: bool


class StreamInput(IdentityInput):
    content: str = Field(min_length=1, max_length=4000)
    profile: Literal['baseline', 'defended'] = 'defended'


def delegated(authorization: str | None = Header(default=None), db=Depends(get_db)):
    return agent_access.authenticate(db, authorization)


@router.post('/agent/preview')
def preview(payload: PreviewInput, principal=Depends(delegated), db=Depends(get_db)):
    from .agent_output import filtered_answer
    user, run = principal
    with transaction(db) as conn:
        agent_access.active_run(conn, run)
        answer = filtered_answer(conn, db, run, payload.answer)
        return {'text': agent_access.vault_for(db, run).restore(answer)}


@router.post('/agent/runs/{run_id}/cancel')
def cancel(run_id: str, user=Depends(customer_user), db=Depends(get_db)):
    return agent_access.cancel_run(db, user, run_id)


@router.post('/agent/runs', status_code=201)
def create(payload: RunInput, user=Depends(customer_user), db=Depends(get_db)):
    return agent_access.create_run(db, user, payload.conversation_id, payload.content, payload.profile)


@router.get('/agent/context')
def context(principal=Depends(delegated), db=Depends(get_db)):
    return agent_access.context(db, *principal)


@router.post('/agent/tools')
async def tool(payload: ToolInput, principal=Depends(delegated), db=Depends(get_db)):
    if len(json.dumps(payload.arguments)) > 8000:
        raise HTTPException(422, 'Tool arguments are too large.')
    return await agent_access.execute_tool(db, *principal, payload.name, payload.arguments)


@router.post('/agent/finish')
def finish(payload: FinishInput, principal=Depends(delegated), db=Depends(get_db)):
    from .agent_output import filtered_answer
    user, run = principal
    vault = agent_access.vault_for(db, run)
    with transaction(db) as conn:
        active = conn.execute('SELECT status FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
        if not active or active[0] not in ('READY', 'RUNNING'):
            raise HTTPException(409, 'Run is already finished.')
        answer = filtered_answer(conn, db, run, payload.answer)
        restored = vault.restore(answer)
        conn.execute('''UPDATE agent_runs SET status=?,completed_at=?,latency_ms=?,input_tokens=?,output_tokens=?,
            response_source='agent_service',answer=?,bound_request_json='{}',vault_json='{}' WHERE id=?''',
            (payload.status, now(), payload.latency_ms, payload.input_tokens, payload.output_tokens, agent_access.trace_safe(answer), run['id']))
        import uuid
        message = {'id': str(uuid.uuid4()), 'conversation_id': run['conversation_id'], 'role': 'assistant', 'content': restored, 'created_at': now()}
        conn.execute('INSERT INTO messages VALUES (:id,:conversation_id,:role,:content,:created_at)', message)
        conn.execute('UPDATE conversations SET updated_at=? WHERE id=?', (message['created_at'], run['conversation_id']))
    return {'message': message, 'run_id': run['id'], 'response_source': 'agent_service',
            'tool_events': db.list_events(run['conversation_id'])[-12:]}


@router.get('/agent/runs')
def runs(conversation_id: str = Query(max_length=64), user=Depends(customer_user), db=Depends(get_db)):
    with db.connect() as conn:
        if not conn.execute('SELECT 1 FROM conversations WHERE id=? AND owner_id=?', (conversation_id, user.id)).fetchone():
            raise HTTPException(404, 'Conversation not found.')
        rows = conn.execute('''SELECT id,status,profile,model,created_at,completed_at,latency_ms,input_tokens,output_tokens
            FROM agent_runs WHERE conversation_id=? AND owner_id=? ORDER BY created_at DESC,rowid DESC LIMIT 50''', (conversation_id, user.id))
        return {'items': [dict(r) for r in rows]}


@router.get('/agent/runs/{run_id}')
def run_detail(run_id: str, user=Depends(customer_user), db=Depends(get_db)):
    with db.connect() as conn:
        row = conn.execute('''SELECT id,status,profile,model,created_at,completed_at,latency_ms,input_tokens,output_tokens,answer
            FROM agent_runs WHERE id=? AND owner_id=?''', (run_id, user.id)).fetchone()
        if not row:
            raise HTTPException(404, 'Run not found.')
        result = dict(row)
        result['tool_calls'] = [{**dict(r), 'arguments': json.loads(r['arguments_json']), 'result': json.loads(r['result_json'])} for r in conn.execute('SELECT * FROM agent_calls WHERE run_id=? ORDER BY ordinal', (run_id,))]
        for call in result['tool_calls']:
            del call['arguments_json']; del call['result_json']
        return result


@router.get('/agent/approvals')
def approvals(conversation_id: str = Query(max_length=64), user=Depends(customer_user), db=Depends(get_db)):
    with db.connect() as conn:
        rows = conn.execute('''SELECT a.* FROM tool_approvals a JOIN agent_runs r ON r.id=a.run_id
            WHERE a.owner_id=? AND r.conversation_id=? ORDER BY a.created_at DESC,a.rowid DESC LIMIT 50''', (user.id, conversation_id))
        return {'items': [dict(id=r['id'], name=r['name'], status=r['status'], arguments=json.loads(r['arguments_json']), expires_at=r['expires_at']) for r in rows]}


@router.post('/agent/approvals/{approval_id}')
async def approve(approval_id: str, payload: ApprovalInput, user=Depends(customer_user), db=Depends(get_db)):
    return await agent_access.approve(db, user, approval_id, payload.approve)


def sse(event, data):
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


@router.post('/conversations/{conversation_id}/stream')
async def stream(conversation_id: str, payload: StreamInput, request: Request, user=Depends(customer_user), db=Depends(get_db)):
    if not db.get_conversation(conversation_id, user.id):
        raise HTTPException(404, 'Conversation not found.')
    with db.connect() as conn:
        agent_access.enabled(conn)
    verdict = inspect_prompt(payload.content)
    if verdict.reason:
        db.append_message(conversation_id, 'user', verdict.text)
        db.add_event(conversation_id, 'input_guard', {}, 'DENY', verdict.reason, False)
        answer = db.append_message(conversation_id, 'assistant', verdict.reply)
        async def rejected():
            yield sse('complete', {'message': answer, 'response_source': 'input_guard', 'tool_events': db.list_events(conversation_id)[-12:]})
        return StreamingResponse(rejected(), media_type='text/event-stream')
    grant = agent_access.create_run(db, user, conversation_id, payload.content, payload.profile)
    db.append_message(conversation_id, 'user', verdict.text)
    async def events():
        yield sse('run', {'run_id': grant['run_id'], 'status': 'RUNNING'})
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(135, connect=5)) as client:
                async with client.stream('POST', setting('AGENT_SERVICE_URL', 'http://127.0.0.1:8093').rstrip('/') + '/run',
                                         headers={'Authorization': 'Bearer ' + grant['delegated_token']}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if await request.is_disconnected():
                            return
                        # Proxy only the documented SSE protocol, never response headers.
                        if line.startswith(('event:', 'data:')) or not line:
                            yield line + '\n'
        except (httpx.HTTPError, ValueError):
            with transaction(db) as conn:
                conn.execute("UPDATE agent_runs SET status='FAILED',completed_at=? WHERE id=? AND status IN ('READY','RUNNING')", (now(), grant['run_id']))
            yield sse('error', {'message': 'The separate assistant service is unavailable or timed out. Your banking actions remain available.'})
        finally:
            # Closing the client stream revokes the delegated capability, including
            # pending proposals. Late model/tool responses cannot reopen this run.
            agent_access.cancel_run(db, user, grant['run_id'])
    return StreamingResponse(events(), media_type='text/event-stream', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
