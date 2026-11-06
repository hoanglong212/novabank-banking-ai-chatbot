from fastapi import APIRouter, Depends, HTTPException, Header
from ... import transfers, vietqr
from ...auth import DemoPrincipal
from ...config import provider, setting
from ...database import Database
from ...dependencies import get_db, current_user, customer_user, assistant_user
from ...schemas import ConversationCreate, SendMessage, DemoToolCheck, TransferArgs, TransferConfirm, VietQRArgs
from ...agent import make_agent
from ...gateway import PolicyGateway
from ...guard import inspect_prompt
from ...tools import ToolDispatcher

router = APIRouter()

def require_own_conversation(db: Database, conversation_id: str, user: DemoPrincipal):
    conversation = db.get_conversation(conversation_id, user.id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')
    return conversation


@router.get('/api/conversations')
async def conversations(user: DemoPrincipal = Depends(assistant_user)):
    return get_db().list_conversations(user.id)


@router.post('/api/conversations', status_code=201)
async def create_conversation(payload: ConversationCreate, user: DemoPrincipal = Depends(assistant_user)):
    return get_db().create_conversation(user.id, payload.title)


@router.delete('/api/conversations/{conversation_id}')
async def delete_conversation(conversation_id: str, user: DemoPrincipal = Depends(assistant_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    db.delete_conversation(conversation_id, user.id)
    return {'deleted': True}


@router.get('/api/conversations/{conversation_id}/messages')
async def get_messages(conversation_id: str, user: DemoPrincipal = Depends(assistant_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return db.list_messages(conversation_id)


@router.get('/api/conversations/{conversation_id}/tool-events')
async def get_events(conversation_id: str, user: DemoPrincipal = Depends(assistant_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return db.list_events(conversation_id)


@router.post('/api/conversations/{conversation_id}/messages')
async def send_message(conversation_id: str, payload: SendMessage, user: DemoPrincipal = Depends(customer_user)):
    if setting('LEGACY_AGENT_TEST_MODE') != 'true':
        raise HTTPException(409, 'Use the /stream endpoint for the isolated assistant and customer approvals.')
    db = get_db()
    with db.connect() as conn:
        from ...agent_access import enabled
        enabled(conn)
    require_own_conversation(db, conversation_id, user)
    # Guard runs before anything is stored or reaches a model.
    verdict = inspect_prompt(payload.content)
    db.append_message(conversation_id, 'user', verdict.text)
    if verdict.reason:
        db.add_event(conversation_id, 'input_guard', {}, 'DENY', verdict.reason, executed=False)
        answer = db.append_message(conversation_id, 'assistant', verdict.reply)
        return {'message': answer, 'tool_events': db.list_events(conversation_id)[-12:], 'response_source': 'input_guard'}
    history = db.list_messages(conversation_id)
    dispatcher = ToolDispatcher(db, PolicyGateway(db))
    agent = make_agent()
    reply = await agent.respond(history, user, conversation_id, dispatcher)
    answer = db.append_message(conversation_id, 'assistant', reply)
    return {'message': answer, 'tool_events': db.list_events(conversation_id)[-12:],
            'response_source': getattr(agent, 'response_source', 'mock')}


@router.post('/api/conversations/{conversation_id}/demo/tool-check')
async def demo_policy_check(conversation_id: str, payload: DemoToolCheck,
                            user: DemoPrincipal = Depends(customer_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return await ToolDispatcher(db, PolicyGateway(db)).dry_run(user, conversation_id, payload.tool_name, payload.arguments)


