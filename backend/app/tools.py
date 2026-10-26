"""All simulated tool execution is centralized behind authorisation."""
import json
from pydantic import ValidationError
from .auth import DemoPrincipal
from .database import Database
from .faq import search
from .gateway import PolicyGateway
from .gateway import TRANSACTION_OWNERS
from .schemas import FaqArgs, BalanceArgs, TransactionArgs, RecentTransactionsArgs, TicketArgs, VietQRArgs, ToolDecision
from . import vietqr


TOOL_MODELS = {
    'search_banking_faq': FaqArgs,
    'get_account_balance': BalanceArgs,
    'get_transaction_status': TransactionArgs,
    'get_recent_transactions': RecentTransactionsArgs,
    'create_support_ticket': TicketArgs,
    'create_vietqr': VietQRArgs,
}

ACCOUNTS = {
    'ACC-ALICE-001': {'balance_vnd': 12500000, 'currency': 'VND'},
    'ACC-BOB-001': {'balance_vnd': 8750000, 'currency': 'VND'},
}
TRANSACTIONS = {
    'TX-1001': {'amount_vnd': 300000, 'status': 'COMPLETED', 'description': 'Transfer to Minh Anh', 'direction': 'out', 'date': '2026-10-24'},
    'TX-1002': {'amount_vnd': 950000, 'status': 'PENDING', 'description': 'Electricity bill', 'direction': 'out', 'date': '2026-10-25'},
    'TX-1003': {'amount_vnd': 45000, 'status': 'COMPLETED', 'description': 'Coffee shop', 'direction': 'out', 'date': '2026-10-26'},
    'TX-1004': {'amount_vnd': 15000000, 'status': 'COMPLETED', 'description': 'Salary credit', 'direction': 'in', 'date': '2026-10-20'},
    'TX-2001': {'amount_vnd': 200000, 'status': 'COMPLETED', 'description': 'Transfer to Gia Bao', 'direction': 'out', 'date': '2026-10-23'},
    'TX-2002': {'amount_vnd': 120000, 'status': 'COMPLETED', 'description': 'Ride-hailing trip', 'direction': 'out', 'date': '2026-10-25'},
    'TX-2003': {'amount_vnd': 5000000, 'status': 'COMPLETED', 'description': 'Freelance payment', 'direction': 'in', 'date': '2026-10-21'},
}

OLLAMA_TOOLS = [
    {'type': 'function', 'function': {'name': 'search_banking_faq', 'description': 'Search curated mock bank support FAQs and general guidance. Prefer this for questions about banking procedures.',
     'parameters': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'Customer question'}}, 'required': ['query']}}},
    {'type': 'function', 'function': {'name': 'get_account_balance', 'description': 'Get the authenticated demo customer\'s account balance. Optional account_id must belong to authenticated user.',
     'parameters': {'type': 'object', 'properties': {'account_id': {'type': 'string', 'description': 'Demo account ID; omit for current user'}}}}},
    {'type': 'function', 'function': {'name': 'get_transaction_status', 'description': 'Get simulated transaction status by transaction ID, only for authenticated owner.',
     'parameters': {'type': 'object', 'properties': {'transaction_id': {'type': 'string'}} , 'required': ['transaction_id']}}},
    {'type': 'function', 'function': {'name': 'get_recent_transactions', 'description': "List the authenticated customer's own most recent transactions (history, spending, income).",
     'parameters': {'type': 'object', 'properties': {'limit': {'type': 'integer', 'description': 'How many, default 5'}}}}},
    {'type': 'function', 'function': {'name': 'create_support_ticket', 'description': 'Create a demo customer support ticket for the authenticated customer.',
     'parameters': {'type': 'object', 'properties': {'subject': {'type': 'string'}, 'description': {'type': 'string'}}, 'required': ['subject','description']}}},
    {'type': 'function', 'function': {'name': 'create_vietqr', 'description': 'Create a VietQR payment code for a bank account the user specified.',
     'parameters': {'type': 'object', 'properties': {'bank': {'type': 'string'}, 'account_no': {'type': 'string'}, 'amount_vnd': {'type': 'integer'},
                    'add_info': {'type': 'string'}, 'account_name': {'type': 'string'}}, 'required': ['bank', 'account_no']}}},
]


class ToolDispatcher:
    def __init__(self, db: Database, gateway: PolicyGateway):
        self.db = db
        self.gateway = gateway

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
            result = {'account_id': account_id, **ACCOUNTS[account_id], 'demo': True}
        elif tool_name == 'get_transaction_status':
            transaction_id = parsed['transaction_id']
            result = {'transaction_id': transaction_id, **TRANSACTIONS[transaction_id], 'demo': True}
        elif tool_name == 'get_recent_transactions':
            owned = sorted((dict(transaction_id=t, **TRANSACTIONS[t]) for t, owner in TRANSACTION_OWNERS.items() if owner == user.id),
                           key=lambda t: t['date'], reverse=True)
            result = {'transactions': owned[:parsed['limit']], 'demo': True}
        elif tool_name == 'create_support_ticket':
            ticket = self.db.create_ticket(user.id, parsed['subject'], parsed['description'])
            result = {'ticket_id': ticket['id'], 'status': ticket['status'], 'demo': True}
        elif tool_name == 'create_vietqr':
            try:
                result = await vietqr.generate(**parsed)
            except vietqr.VietQRError as exc:
                result = {'error': 'TOOL_FAILED', 'reason_code': exc.reason_code}
        else:
            # Defensive deny; impossible without a programming error upstream.
            result = {'error': 'TOOL_DENIED', 'reason_code': 'UNKNOWN_TOOL'}
            self.db.add_event(conversation_id, tool_name, {}, 'DENY', 'UNKNOWN_TOOL', executed=False)
            return result
        self.db.add_event(conversation_id, tool_name, parsed, 'ALLOW', decision.reason_code, executed=True)
        return result
