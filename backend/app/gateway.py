"""Policy decision point; NEVER executes tools.

Local policy is a development placeholder. Remote contract is intentionally proposed,
not represented as the team's actual gateway implementation.
"""
import httpx
from .auth import DemoPrincipal
from .config import setting
from .database import Database
from .schemas import ToolDecision


VALID_TOOLS = {'search_banking_faq', 'get_account_balance', 'get_transaction_status', 'get_recent_transactions',
               'create_support_ticket', 'create_vietqr', 'create_transfer'}
# Every argument naming an account the tool reads or debits, whatever the tool. A new tool is covered
# as long as it uses one of these names; omitted means the caller's own account.
OWNED_ACCOUNT_ARGS = ('account_id', 'from_account')


class PolicyGateway:
    def __init__(self, db: Database, mode: str | None = None, url: str | None = None):
        self.db = db
        self.mode = mode or setting('GATEWAY_MODE', 'local')
        self.url = url if url is not None else setting('GATEWAY_URL', '')

    async def authorize(self, principal: DemoPrincipal, conversation_id: str, tool_name: str, arguments: dict) -> ToolDecision:
        if tool_name not in VALID_TOOLS:
            return ToolDecision(decision='DENY', reason_code='UNKNOWN_TOOL')
        # Unknown and foreign IDs get the same reason code, so denials do not reveal which accounts exist.
        if any(arguments.get(key) not in (None, *principal.accounts) for key in OWNED_ACCOUNT_ARGS):
            return ToolDecision(decision='DENY', reason_code='ACCOUNT_NOT_OWNED')
        if 'transaction_id' in arguments:
            transaction = self.db.transaction(arguments['transaction_id'])
            if transaction is None or transaction['owner_id'] != principal.id:
                return ToolDecision(decision='DENY', reason_code='TRANSACTION_NOT_OWNED')
        if self.mode == 'local':
            return ToolDecision(decision='ALLOW', reason_code='LOCAL_POLICY_APPROVED')
        if self.mode != 'remote' or not self.url:
            return ToolDecision(decision='DENY', reason_code='GATEWAY_NOT_CONFIGURED')
        # Fail closed: only authenticated demo principal injected by API, never agent role claims.
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(self.url.rstrip('/') + '/authorize', json={
                    'principal_id': principal.id,
                    'conversation_id': conversation_id,
                    'tool_name': tool_name,
                    'arguments': arguments,
                })
                response.raise_for_status()
                decision = response.json().get('decision')
                if decision == 'ALLOW':
                    return ToolDecision(decision='ALLOW', reason_code='REMOTE_POLICY_APPROVED')
                return ToolDecision(decision='DENY', reason_code='REMOTE_POLICY_DENIED')
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return ToolDecision(decision='DENY', reason_code='REMOTE_GATEWAY_UNAVAILABLE')
