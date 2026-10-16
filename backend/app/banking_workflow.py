"""Constrained demo workflows. User text binds resources; model text is never authority.

This is application orchestration, not a claim that an LLM independently inferred
the right tool. All execution still goes through ToolDispatcher authorization.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import re

from .faq import fold


@dataclass
class BankingRequest:
    tool: str | None = None
    arguments: dict = field(default_factory=dict)
    reply: str | None = None
    amount_vnd: int | None = None
    affordability: bool = False


BALANCE_WORDS = ('so du', 'balance', 'tai khoan con', 'con bao nhieu', 'kiem tra tien')
FOLLOW_BALANCE = ('du tien', 'du khong', 'enough money', 'afford')


def account_in(text: str) -> str | None:
    explicit = re.search(r'\bACC-[A-Z0-9]+-[A-Z0-9-]+\b', text, re.I)
    if explicit:
        return explicit.group().upper()
    # Preserve explicitly supplied unknown IDs too; never replace them with self.
    explicit = re.search(r'\b(?:tai khoan|account)(?:\s+(?:id|so|number))?[\s:#]+([a-z]*\d[a-z0-9-]*)\b', fold(text))
    return explicit.group(1).upper() if explicit else None


def requested_amount(text: str) -> int | None:
    match = re.search(r'\b(?:chuyen|rut|thanh toan|transfer|withdraw)\s+(\d+(?:[.,]\d+)?)\s*(trieu|nghin|ngan|million|thousand)\b', text)
    if not match:
        return None
    multiplier = 1_000_000 if match.group(2) in ('trieu', 'million') else 1000
    return int(Decimal(match.group(1).replace(',', '.')) * multiplier)


def bind_request(messages: list[dict]) -> BankingRequest:
    question = messages[-1]['content'].strip()
    text = fold(question)
    history = [m['content'] for m in messages[:-1] if m['role'] == 'user'][-12:]
    wants_ticket = bool(re.search(
        r'\b(?:tao|mo|lap|create|open)\s+(?:(?:giup|cho)\s+(?:toi|minh)\s+)?'
        r'(?:(?:mot|1|a|a new|new)\s+)?'
        r'(?:phieu ho tro|yeu cau ho tro|khieu nai|ticket|support ticket|support request)\b', text))
    ticket_is_question = any(term in text for term in (
        'huong dan', 'cach tao', 'cach mo', 'cach lap', 'lam sao', 'nghia la',
        'la gi', 'how to', 'how do', 'what is', 'neu ', 'if '))
    ticket_is_negated = 'khong muon' in text or 'do not want' in text or bool(re.search(
        r'\b(?:khong|dung|chua|do not|don.t)\b.{0,35}\b(?:tao|mo|lap|create|open)\b', text))
    if wants_ticket and not ticket_is_question and not ticket_is_negated:
        return BankingRequest('create_support_ticket', {
            'subject': 'Customer support request (demo)',
            'description': question,
        })

    ids = re.findall(r'\bTX-[A-Z0-9-]+\b', question, re.I)
    if not ids and any(term in text for term in ('giao dich do', 'giao dich nay', 'that transaction', 'its status')):
        # Resolve references from user-originated messages only, never model guesses.
        for previous in reversed(history):
            ids = re.findall(r'\bTX-[A-Z0-9-]+\b', previous, re.I)
            if ids:
                break
    if ids and not wants_ticket:
        if len(set(x.upper() for x in ids)) > 1:
            return BankingRequest(reply='Please choose one demo transaction ID to check at a time.')
        return BankingRequest('get_transaction_status', {'transaction_id': ids[-1].upper()})

    balance = any(term in text for term in BALANCE_WORDS)
    affordability = any(term in text for term in FOLLOW_BALANCE)
    explicit_account = account_in(question)
    if balance or affordability or explicit_account:
        account = explicit_account
        if not account and affordability:
            for previous in reversed(history):
                if any(term in fold(previous) for term in BALANCE_WORDS):
                    account = account_in(previous)
                    break
        # A named third party is not an instruction to substitute the current user.
        if not account and re.search(r'\b(?:bob|alice|gia bao|minh anh|nguoi khac)\b', text):
            return BankingRequest(reply='Please provide the demo account ID to check. You can only view accounts you own.')
        return BankingRequest('get_account_balance', {'account_id': account} if account else {},
                              amount_vnd=requested_amount(text), affordability=affordability)

    if re.search(r'^(?:(?:hay|vui long|giup toi)\s+)?(?:chuyen|rut|transfer|withdraw)\b', text):
        return BankingRequest(reply='This demo does not support transfers or withdrawals. No transaction has been performed.')
    if re.search(r'\b(?:xin chao|hello|hi|ban co the giup|ban lam duoc|what can you)\b', text):
        return BankingRequest(reply='Hello! I am your NovaBank demo assistant. I can answer banking and VietQR questions, check demo balances and transactions, or create a support ticket at your request. Real transfers are not supported. Never share OTPs, PINs, or real banking data.')
    if text.rstrip('.! ') in ('cam on', 'cam on ban', 'thank you', 'thanks'):
        return BankingRequest(reply='Happy to help! Feel free to ask another banking question or explore the demo data.')
    # Unrecognized questions use the approved KB, not unconstrained model prose.
    return BankingRequest('search_banking_faq', {'query': question})


def vnd(amount: int) -> str:
    return f'{amount:,} VND'


def render_result(request: BankingRequest, result: dict) -> str:
    if 'error' in result:
        return f'Request blocked ({result["reason_code"]}). No data was returned and no tool was executed for this request.'
    if request.tool == 'get_account_balance':
        answer = f'The balance of demo account **{result["account_id"]}** is **{vnd(result["balance_vnd"])}**.'
        if request.affordability:
            if request.amount_vnd is None:
                answer += ' Please specify the planned amount clearly (for example, 3 million) so I can compare it.'
            elif request.amount_vnd > 0:
                enough = 'have enough funds' if result['balance_vnd'] >= request.amount_vnd else 'do not have enough funds'
                answer += f' You {enough} for the planned amount of **{vnd(request.amount_vnd)}**, before fees and limits.'
            else:
                answer += ' The planned amount must be greater than zero.'
            answer += ' No transaction has been performed.'
        return answer + ' This is simulated data.'
    if request.tool == 'get_transaction_status':
        explanation = {'PENDING': 'Processing is pending; the transaction has not completed.', 'COMPLETED': 'The simulated transaction has completed.'}.get(result['status'], '')
        return f'Demo transaction **{result["transaction_id"]}** has status **{result["status"]}** and amount **{vnd(result["amount_vnd"])}**. {explanation}'
    if request.tool == 'create_support_ticket':
        return f'Created demo support ticket **{result["ticket_id"]}**, status **{result["status"]}**. No personal information is needed. No request was sent to a real bank.'
    matches = result.get('matches', [])
    if matches:
        return matches[0]['answer']
    return 'I could not find reliable information about this question in the demo FAQ. Please check your bank\'s official channels. I cannot invent fees or policies.'
