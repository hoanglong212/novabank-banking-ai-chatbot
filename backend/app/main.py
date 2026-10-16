"""Banking demo HTTP API; ownership checks are applied on every conversation route."""
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from .agent import make_agent
from .auth import DemoPrincipal, DEMO_USERS, authenticate
from .config import provider, setting
from .database import Database
from .gateway import PolicyGateway
from .schemas import ConversationCreate, SendMessage, DemoToolCheck
from .tools import ToolDispatcher


def get_db() -> Database:
    return Database(setting('DB_PATH', './novabank_demo.sqlite3'))


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db().initialize()
    yield


app = FastAPI(title='NovaBank Banking Chatbot (Demo Only)', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
                   allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])


def current_user(authorization: str | None = Header(default=None)) -> DemoPrincipal:
    return authenticate(authorization)


def require_own_conversation(db: Database, conversation_id: str, user: DemoPrincipal):
    conversation = db.get_conversation(conversation_id, user.id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')
    return conversation


@app.get('/api/health')
async def health():
    return {'status': 'ok', 'llm_provider': provider(), 'gateway_mode': setting('GATEWAY_MODE', 'local'), 'demo_only': True}


@app.get('/api/demo/users')
async def demo_users():
    # Exposes local demo identity tokens intentionally; NEVER deploy to the public internet.
    return [{'id': u.id, 'name': u.name, 'token': u.token} for u in DEMO_USERS]


@app.get('/api/conversations')
async def conversations(user: DemoPrincipal = Depends(current_user)):
    return get_db().list_conversations(user.id)


@app.post('/api/conversations', status_code=201)
async def create_conversation(payload: ConversationCreate, user: DemoPrincipal = Depends(current_user)):
    return get_db().create_conversation(user.id, payload.title)


@app.delete('/api/conversations/{conversation_id}')
async def delete_conversation(conversation_id: str, user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    db.delete_conversation(conversation_id, user.id)
    return {'deleted': True}


@app.get('/api/conversations/{conversation_id}/messages')
async def get_messages(conversation_id: str, user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return db.list_messages(conversation_id)


@app.get('/api/conversations/{conversation_id}/tool-events')
async def get_events(conversation_id: str, user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return db.list_events(conversation_id)


@app.post('/api/conversations/{conversation_id}/messages')
async def send_message(conversation_id: str, payload: SendMessage, user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    db.append_message(conversation_id, 'user', payload.content)
    history = db.list_messages(conversation_id)
    dispatcher = ToolDispatcher(db, PolicyGateway())
    agent = make_agent()
    reply = await agent.respond(history, user, conversation_id, dispatcher)
    answer = db.append_message(conversation_id, 'assistant', reply)
    return {'message': answer, 'tool_events': db.list_events(conversation_id)[-12:],
            'response_source': getattr(agent, 'response_source', 'mock')}


@app.post('/api/conversations/{conversation_id}/demo/tool-check')
async def demo_policy_check(conversation_id: str, payload: DemoToolCheck,
                            user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return await ToolDispatcher(db, PolicyGateway()).dry_run(user, conversation_id, payload.tool_name, payload.arguments)
