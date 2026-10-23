"""All simulated tool execution is centralized behind authorisation."""
import json
from pydantic import ValidationError
from .auth import DemoPrincipal
from .database import Database
from .faq import search
from .gateway import PolicyGateway
from .schemas import FaqArgs, BalanceArgs, TransactionArgs, ToolDecision
from .banking import accounts_for, transactions_for


TOOL_MODELS = {
    'search_banking_faq': FaqArgs,
    'get_account_balance': BalanceArgs,
    'get_transaction_status': TransactionArgs,
}

OLLAMA_TOOLS = [
    {'type': 'function', 'function': {'name': 'search_banking_faq', 'description': 'Search curated mock bank support FAQs and general guidance. Prefer this for questions about banking procedures.',
     'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'Customer question'}}, 'required': ['query']}}},
    {'type': 'function', 'function': {'name': 'get_account_balance', 'description': 'Get the authenticated demo customer\'s account balance. Optional account_id must belong to authenticated user.',
     'parameters': {'type': 'object', 'properties': {'account_id': {'type': 'string', 'description': 'Demo account ID; omit for current user'}}}}},
    {'type': 'function', 'function': {'name': 'get_transaction_status', 'description': 'Get simulated transaction status by transaction ID, only for authenticated owner.',
     'parameters': {'type': 'object', 'properties': {'transaction_id': {'type': 'string'}} , 'required': ['transaction_id']}}},
]


class ToolDispatcher:
    def __init__(self, db: Database, gateway: PolicyGateway):
        self.db = db
        self.gateway = gateway
        self.gateway.database = db

    def record_rejection(self, conversation_id: str, tool_name: str, reason_code: str):
        """Audit an unrequested model proposal without persisting model-supplied PII."""
        self.db.add_event(conversation_id, tool_name[:80], {}, 'DENY', reason_code, executed=False)

    def _validate(self, tool_name: str, arguments):
        model = TOOL_MODELS.get(tool_name)
        if model is None:
            return None, 'UNKNOWN_TOOL'
        if not isinstance(arguments, dict):
            return None, 'INVALID_ARGUMENTS'
        try:
            parsed = model.model_validate(arguments)
            return parsed.model_dump(exclude_none=True), None
        except ValidationError:
            return None, 'INVALID_ARGUMENTS'

    async def _decide(self, user: DemoPrincipal, conversation_id: str, tool_name: str, arguments):
        parsed, error = self._validate(tool_name, arguments)
        if error:
            return ToolDecision(decision='DENY', reason_code=error), parsed
        return await self.gateway.authorize(user, conversation_id, tool_name, parsed), parsed

    async def dry_run(self, user: DemoPrincipal, conversation_id: str, tool_name: str, arguments):
        decision, parsed = await self._decide(user, conversation_id, tool_name, arguments)
        self.db.add_event(conversation_id, tool_name, parsed if parsed is not None else {}, decision.decision,
                          decision.reason_code, executed=False)
        return {'decision': decision.decision, 'reason_code': decision.reason_code, 'executed': False}

    async def run(self, user: DemoPrincipal, conversation_id: str, tool_name: str, arguments):
        decision, parsed = await self._decide(user, conversation_id, tool_name, arguments)
        if decision.decision != 'ALLOW':
            self.db.add_event(conversation_id, tool_name, parsed if parsed is not None else {},
                              'DENY', decision.reason_code, executed=False)
            return {'error': 'TOOL_DENIED', 'reason_code': decision.reason_code}
        # Only this branch can execute a tool; agent itself has no banking DB access.
        if tool_name == 'search_banking_faq':
            result = search(parsed['query'])
        elif tool_name == 'get_account_balance':
            account_id = parsed.get('account_id') or user.accounts[0]
            account = next(a for a in accounts_for(self.db,user.id) if a['id']==account_id)
            result = {'account_id':account_id,'balance_vnd':account['balance_vnd'],'currency':account['currency'],'demo':True}
        elif tool_name == 'get_transaction_status':
            transaction_id = parsed['transaction_id']
            transaction = transactions_for(self.db,user.id,transaction_id)[0]
            result = {'transaction_id':transaction_id,'amount_vnd':transaction['amount_vnd'],'status':transaction['status'],'demo':True}
        else:
            # Defensive deny; impossible without a programming error upstream.
            result = {'error': 'TOOL_DENIED', 'reason_code': 'UNKNOWN_TOOL'}
            self.db.add_event(conversation_id, tool_name, {}, 'DENY', 'UNKNOWN_TOOL', executed=False)
            return result
        self.db.add_event(conversation_id, tool_name, parsed, 'ALLOW', decision.reason_code, executed=True)
        return result
