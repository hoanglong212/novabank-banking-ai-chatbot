"""Banking demo HTTP API; ownership checks are applied on every conversation route."""
from contextlib import asynccontextmanager
import asyncio
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from .agent import make_agent
from . import transfers, vietqr
from .auth import DemoPrincipal
from .config import provider, setting
from .database import Database
from .gateway import PolicyGateway
from .guard import inspect_prompt
from .schemas import ConversationCreate, SendMessage, DemoToolCheck, LoginRequest, TransferArgs, TransferConfirm, VietQRArgs
from .tools import ToolDispatcher
from .readiness import readiness
from .web import mount_frontend
from .dependencies import get_db, current_user, customer_user
from .routes_banking import router as banking_router
from .routes_identity import router as identity_router
from .routes_sessions import router as sessions_router
from .routes_customer import router as customer_router
from .routes_insights import router as insights_router
from .routes_support import router as support_router
from .routes_admin import router as admin_router
from .routes_qr import router as qr_router
from .routes_knowledge import router as knowledge_router
from .routes_agent import router as agent_router
from .routes_research import router as research_router
from .http_security import HttpSecurity


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db().initialize()
    from .workers import loop
    task = asyncio.create_task(loop(get_db())) if setting('BANK_WORKER_ENABLED', 'true').lower() == 'true' else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def safe_validation_error(request, exc):
    # Pydantic's default detail includes raw input (including invalid passwords).
    if request.url.path.startswith(('/api/auth/', '/api/customer/profile/', '/api/actions/')):
        return JSONResponse(status_code=422, content={'detail': 'Please check the form fields and try again.'},
                            headers={'Cache-Control': 'no-store'})
    return await request_validation_exception_handler(request, exc)


async def health():
    return {'status': 'ok', 'llm_provider': provider(), 'gateway_mode': setting('GATEWAY_MODE', 'local'), 'demo_only': True,
            'agent_mode': 'legacy_test' if setting('LEGACY_AGENT_TEST_MODE') == 'true' else 'service'}






async def me(user: DemoPrincipal = Depends(current_user)):
    # Direct read of the signed-in customer's own demo data; the agent still goes through ToolDispatcher.
    db = get_db()
    return {'id': user.id, 'name': user.name, 'role': user.role, 'permissions': sorted(user.permissions),
            'accounts': [{'id': a['id'], 'holder_name': a['holder_name'], 'balance_vnd': a['balance_vnd'], 'currency': 'VND'}
                         for a in db.accounts_of(user.id)],
            'transactions': db.transactions_of(user.id)}



from .api.routes.transfers import router as transfers_router, transfer_failed
from .api.routes.chat import router as chat_router, require_own_conversation
from .api.routes.dev import router as dev_router


def create_app():
    application = FastAPI(title='NovaBank Banking Chatbot (Demo Only)', version='0.1.0', lifespan=lifespan)
    application.add_exception_handler(RequestValidationError, safe_validation_error)
    origins = [value.strip() for value in setting('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if value.strip()]
    if '*' in origins:
        raise RuntimeError('CORS_ORIGINS must list explicit trusted origins')
    application.add_middleware(CORSMiddleware, allow_origins=origins,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key', 'X-Request-ID'], expose_headers=['X-Request-ID'])
    application.add_middleware(HttpSecurity)
    for router in (customer_router, insights_router, support_router, admin_router, qr_router, knowledge_router,
                   agent_router, research_router, transfers_router, chat_router, dev_router,
                   banking_router, identity_router, sessions_router):
        application.include_router(router)
    application.add_api_route('/api/health', health, methods=['GET'])
    application.add_api_route('/api/ready', readiness, methods=['GET'])
    application.add_api_route('/api/me', me, methods=['GET'])
    if setting('FRONTEND_DIST'):
        mount_frontend(application, setting('FRONTEND_DIST'))
    return application


app = create_app()
