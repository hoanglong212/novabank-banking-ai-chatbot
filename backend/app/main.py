"""Banking demo HTTP API; ownership checks are applied on every conversation route."""
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from .agent import make_agent
from . import transfers, vietqr
from .auth import DemoPrincipal, TTL_SECONDS, authenticate, issue_token, login
from .config import provider, setting
from .database import Database
from .gateway import PolicyGateway
from .guard import inspect_prompt
from .schemas import ConversationCreate, SendMessage, DemoToolCheck, LoginRequest, TransferArgs, TransferConfirm, VietQRArgs
from .tools import ToolDispatcher
from .readiness import readiness
from .web import mount_frontend


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


app.add_api_route('/api/ready', readiness, methods=['GET'])


@app.post('/api/auth/login')
async def sign_in(payload: LoginRequest):
    user = login(payload.username, payload.password)
    return {'access_token': issue_token(user), 'token_type': 'bearer', 'expires_in': TTL_SECONDS,
            'user': {'id': user.id, 'name': user.name}}


@app.get('/api/me')
async def me(user: DemoPrincipal = Depends(current_user)):
    # Direct read of the signed-in customer's own demo data; the agent still goes through ToolDispatcher.
    db = get_db()
    return {'id': user.id, 'name': user.name,
            'accounts': [{'id': a['id'], 'holder_name': a['holder_name'], 'balance_vnd': a['balance_vnd'], 'currency': 'VND'}
                         for a in db.accounts_of(user.id)],
            'transactions': db.transactions_of(user.id)}


def transfer_failed(exc: transfers.TransferError) -> HTTPException:
    status = {'TRANSFER_NOT_FOUND': 404, 'VIETQR_UNAVAILABLE': 502}.get(exc.reason_code, 400)
    return HTTPException(status_code=status, detail=exc.reason_code)


@app.post('/api/transfers', status_code=201)
async def create_transfer(payload: TransferArgs, user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    try:
        draft = await transfers.prepare(db, user, payload.model_dump(exclude_none=True))
        draft, otp = transfers.issue_otp(db, user, draft['id'])
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc
    # demo_otp stands in for the SMS a real bank would send; it never reaches the assistant.
    return {**transfers.public(draft), 'demo_otp': otp}


@app.post('/api/transfers/{transfer_id}/otp')
async def resend_transfer_otp(transfer_id: str, user: DemoPrincipal = Depends(current_user)):
    try:
        draft, otp = transfers.issue_otp(get_db(), user, transfer_id)
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc
    return {**transfers.public(draft), 'demo_otp': otp}


@app.post('/api/transfers/{transfer_id}/confirm')
async def confirm_transfer(transfer_id: str, payload: TransferConfirm, user: DemoPrincipal = Depends(current_user)):
    try:
        return transfers.confirm(get_db(), user, transfer_id, payload.otp)
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc


@app.get('/api/vietqr/banks')
async def vietqr_banks(user: DemoPrincipal = Depends(current_user)):
    try:
        return [{k: b.get(k) for k in ('bin', 'code', 'shortName', 'name', 'logo')} for b in await vietqr.banks()]
    except vietqr.VietQRError as exc:
        raise HTTPException(status_code=502, detail='VietQR bank list is unavailable') from exc


@app.post('/api/vietqr')
async def create_vietqr(payload: VietQRArgs, user: DemoPrincipal = Depends(current_user)):
    try:
        return await vietqr.generate(**payload.model_dump(exclude_none=True))
    except vietqr.VietQRError as exc:
        raise HTTPException(status_code=400 if exc.reason_code == 'UNKNOWN_BANK' else 502, detail=exc.reason_code) from exc


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


@app.post('/api/conversations/{conversation_id}/demo/tool-check')
async def demo_policy_check(conversation_id: str, payload: DemoToolCheck,
                            user: DemoPrincipal = Depends(current_user)):
    db = get_db()
    require_own_conversation(db, conversation_id, user)
    return await ToolDispatcher(db, PolicyGateway(db)).dry_run(user, conversation_id, payload.tool_name, payload.arguments)


if setting('FRONTEND_DIST'):
    mount_frontend(app, setting('FRONTEND_DIST'))
