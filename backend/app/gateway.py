"""Policy decision point; NEVER executes tools.

Local policy is a development placeholder. Remote contract is intentionally proposed,
not represented as the team's actual gateway implementation.
"""
import httpx
from .auth import DemoPrincipal
from .config import setting
from .schemas import ToolDecision


VALID_TOOLS = {'search_banking_faq', 'get_account_balance', 'get_transaction_status', 'get_recent_transactions',
               'create_support_ticket', 'create_vietqr'}
ACCOUNT_OWNERS = {'ACC-ALICE-001': 'alice', 'ACC-BOB-001': 'bob'}
TRANSACTION_OWNERS = {'TX-1001': 'alice', 'TX-1002': 'alice', 'TX-1003': 'alice', 'TX-1004': 'alice',
                      'TX-2001': 'bob', 'TX-2002': 'bob', 'TX-2003': 'bob'}


class PolicyGateway:
    def __init__(self, mode: str | None = None, url: str | None = None):
        self.mode = mode or setting('GATEWAY_MODE', 'local')
        self.url = url if url is not None else setting('GATEWAY_URL', '')

    async def authorize(self, principal: DemoPrincipal, conversation_id: str, tool_name: str, arguments: dict) -> ToolDecision:
        if tool_name not in VALID_TOOLS:
            return ToolDecision(decision='DENY', reason_code='UNKNOWN_TOOL')
        if tool_name == 'get_account_balance':
            account_id = arguments.get('account_id') or principal.accounts[0]
            if ACCOUNT_OWNERS.get(account_id) != principal.id:
                return ToolDecision(decision='DENY', reason_code='ACCOUNT_NOT_OWNED')
        if tool_name == 'get_transaction_status':
            if TRANSACTION_OWNERS.get(arguments.get('transaction_id')) != principal.id:
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
