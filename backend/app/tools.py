"""All simulated tool execution is centralized behind authorisation."""
import json
from pydantic import ValidationError
from .auth import DemoPrincipal
from .database import Database
from .faq import search
from .gateway import PolicyGateway
from .schemas import FaqArgs, BalanceArgs, TransactionArgs, RecentTransactionsArgs, TicketArgs, VietQRArgs, TransferArgs, ToolDecision
from . import transfers, vietqr


TOOL_MODELS = {
    'search_banking_faq': FaqArgs,
    'get_account_balance': BalanceArgs,
    'get_transaction_status': TransactionArgs,
    'get_recent_transactions': RecentTransactionsArgs,
    'create_support_ticket': TicketArgs,
    'create_vietqr': VietQRArgs,
    'create_transfer': TransferArgs,
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
    {'type': 'function', 'function': {'name': 'create_transfer', 'description': 'Prepare a money transfer draft from the customer own account when they explicitly ask to send money. Nothing is sent: the customer reviews it and confirms with an OTP in the app.',
     'parameters': {'type': 'object', 'properties': {'to_bank': {'type': 'string', 'description': 'NovaBank for internal IDs like ACC-BOB-001, else the bank name'},
                    'to_account': {'type': 'string'}, 'amount_vnd': {'type': 'integer'}, 'content': {'type': 'string'}}, 'required': ['to_account', 'amount_vnd']}}},
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
            account = self.db.account(parsed.get('account_id') or user.accounts[0])
            result = {'account_id': account['id'], 'balance_vnd': account['balance_vnd'], 'currency': 'VND', 'demo': True}
        elif tool_name == 'get_transaction_status':
            tx = self.db.transaction(parsed['transaction_id'])
            result = {'transaction_id': tx['id'], **{k: tx[k] for k in ('amount_vnd', 'status', 'description', 'direction', 'date')}, 'demo': True}
        elif tool_name == 'get_recent_transactions':
            owned = self.db.transactions_of(user.id, parsed['limit'])
            result = {'transactions': [{'transaction_id': t.pop('id'), **t} for t in owned], 'demo': True}
        elif tool_name == 'create_support_ticket':
            ticket = self.db.create_ticket(user.id, parsed['subject'], parsed['description'])
            result = {'ticket_id': ticket['id'], 'status': ticket['status'], 'demo': True}
        elif tool_name == 'create_vietqr':
            try:
                result = await vietqr.generate(**parsed)
            except vietqr.VietQRError as exc:
                result = {'error': 'TOOL_FAILED', 'reason_code': exc.reason_code}
        elif tool_name == 'create_transfer':
            try:
                draft = await transfers.prepare(self.db, user, parsed)
                # No recipient name and no OTP: the model gets only what the customer already typed.
                result = {'transfer_id': draft['id'], 'to_bank': draft['to_bank'], 'to_account': draft['to_account'],
                          'amount_vnd': draft['amount_vnd'], 'status': draft['status'], 'demo': True}
            except transfers.TransferError as exc:
                result = {'error': 'TOOL_FAILED', 'reason_code': exc.reason_code}
        else:
            # Defensive deny; impossible without a programming error upstream.
            result = {'error': 'TOOL_DENIED', 'reason_code': 'UNKNOWN_TOOL'}
            self.db.add_event(conversation_id, tool_name, {}, 'DENY', 'UNKNOWN_TOOL', executed=False)
            return result
        self.db.add_event(conversation_id, tool_name, parsed, 'ALLOW', decision.reason_code, executed=True)
        return result
