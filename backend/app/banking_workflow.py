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


def bank_in(text: str, account: str) -> str | None:
    # "ngan hang X" / "bank X", then "<account> X", then "X account <account>".
    bank = (re.search(r'\b(?:ngan hang|bank|tai(?! khoan)|at)\s+([a-z0-9]{2,})', text)
            or re.search(re.escape(account) + r'\s+(?!(?:noi|so|voi|va|and|with|amount|content|note)\b)([a-z][a-z0-9]+)', text)
            or re.search(r'\b([a-z0-9]{2,})\s+(?:account|tai khoan|stk)\b', text))
    return bank.group(1) if bank else None


def amount_in(text: str) -> int | None:
    amount = re.search(r'(\d+(?:[.,]\d+)*)\s*(k|nghin|ngan|tr|trieu|m|million|thousand|vnd|dong|d)?\b', text)
    if not amount:
        return None
    unit = {'k': 1000, 'nghin': 1000, 'ngan': 1000, 'thousand': 1000,
            'tr': 1_000_000, 'trieu': 1_000_000, 'm': 1_000_000, 'million': 1_000_000}.get(amount.group(2) or '')
    number = amount.group(1)
    value = Decimal(number.replace(',', '.')) * unit if unit else Decimal(re.sub(r'[.,]', '', number))
    return int(value) if value > 0 else None


CONTENT = re.compile(r'\b(?:noi dung|content|note|message|ghi chu|memo)\s*:?\s*(.+)$')


def content_in(text: str) -> str | None:
    info = CONTENT.search(text)
    return info.group(1).strip(' ."\'') if info else None


NOVA_ID = r'\bACC-[A-Z0-9]+-[A-Z0-9-]+\b'
TRANSFER_HELP = ('To transfer, tell me the amount and the recipient, for example: "Transfer 200k to ACC-BOB-001 '
                 'content lunch" or "Transfer 500k to Vietcombank account 0123456789". You confirm it with an OTP in the app.')


def transfer_request(question: str, text: str) -> BankingRequest:
    """Recipient, amount and payer come only from the customer's own words; the gateway checks the payer."""
    source = re.search(r'\b(?:from|tu)\s+(' + NOVA_ID + ')', question, re.I)
    internal = [x.upper() for x in re.findall(NOVA_ID, question, re.I) if not source or x.upper() != source.group(1).upper()]
    head = CONTENT.split(text)[0]  # an amount inside the transfer content is not the amount
    if internal:
        args = {'to_bank': 'NovaBank', 'to_account': internal[0]}
        rest = re.sub(NOVA_ID, ' ', head, flags=re.I)
    else:
        numbers = re.findall(r'(?<!\d)\d{6,19}(?!\d)', head)
        keyed = re.search(r'\b(?:account|tai khoan|stk)(?:\s*(?:no|number|so))?\s*[:#]?\s*(\d{6,19})\b', head)
        account = keyed.group(1) if keyed else max(numbers, key=len, default=None)
        bank = account and bank_in(head, account)
        if not bank:
            return BankingRequest(reply=TRANSFER_HELP)
        args = {'to_bank': bank, 'to_account': account}
        rest = head.replace(account, ' ')
    amount = amount_in(rest)
    if not amount:
        return BankingRequest(reply=TRANSFER_HELP)
    args['amount_vnd'] = amount
    if source:
        args['from_account'] = source.group(1).upper()
    info = content_in(text)
    if info:
        args['content'] = info
    return BankingRequest('create_transfer', args)


QR_HELP = ('To create a VietQR code, tell me the bank and the account number, for example: '
           '"Create a QR for Vietcombank account 0123456789, 500k, content dinner".')


def qr_request(question: str, text: str) -> BankingRequest | None:
    if not (re.search(r'\b(?:viet)?qr\b', text) and re.search(r'\b(?:tao|lap|xuat|create|generate|make)\b', text)):
        return None
    # The number introduced as the account wins; otherwise the longest one (amounts are usually shorter).
    keyed = re.search(r'\b(?:account|tai khoan|stk)(?:\s*(?:no|number|so))?\s*[:#]?\s*(\d{6,19})\b', text)
    numbers = re.findall(r'(?<!\d)\d{6,19}(?!\d)', text)
    account = keyed.group(1) if keyed else max(numbers, key=len, default=None)
    if not account:
        return BankingRequest(reply=QR_HELP)
    bank = bank_in(text, account)
    if not bank:
        return BankingRequest(reply=QR_HELP)
    args = {'bank': bank, 'account_no': account}
    amount = amount_in(text.replace(account, ' '))
    if amount:
        args['amount_vnd'] = amount
    info = content_in(text)
    if info:
        args['add_info'] = info
    name = re.search(r'(?i:\bt[eê]n|account name)\s*:?\s*([A-Z]{2,}(?: [A-Z]{1,})+)', question)
    if name:
        args['account_name'] = name.group(1)
    return BankingRequest('create_vietqr', args)


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

    qr = qr_request(question, text)
    if qr:
        return qr

    # Before the balance branch: "transfer 200k to ACC-BOB-001" names an account but is not a balance check.
    if re.search(r'^(?:(?:hay|vui long|giup toi)\s+)?(?:chuyen|transfer|send)\b', text):
        return transfer_request(question, text)

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

    if re.search(r'\b(?:recent transactions|transaction history|my transactions|lich su giao dich|giao dich gan day)\b', text):
        return BankingRequest('get_recent_transactions', {'limit': 5})

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

    if re.search(r'^(?:(?:hay|vui long|giup toi)\s+)?(?:rut|withdraw)\b', text):
        return BankingRequest(reply='Cash withdrawals need an ATM or a branch. No transaction has been performed.')
    if re.search(r'\b(?:xin chao|hello|hi|ban co the giup|ban lam duoc|what can you)\b', text):
        return BankingRequest(reply='Hello! I am your NovaBank demo assistant. I can answer banking and VietQR questions, check demo balances and transactions, prepare a transfer for you to confirm with an OTP, or create a support ticket at your request. Never share OTPs, PINs, or real banking data.')
    if text.rstrip('.! ') in ('cam on', 'cam on ban', 'thank you', 'thanks'):
        return BankingRequest(reply='Happy to help! Feel free to ask another banking question or explore the demo data.')
    # Unrecognized questions use the approved KB, not unconstrained model prose.
    return BankingRequest('search_banking_faq', {'query': question})


def vnd(amount: int) -> str:
    return f'{amount:,} VND'


def render_qr(result: dict) -> str:
    amount = f' for **{vnd(result["amount_vnd"])}**' if result.get('amount_vnd') else ''
    info = f' with content "{result["add_info"]}"' if result.get('add_info') else ''
    # The chat UI renders this line as an image only for VietQR sources.
    return (f'VietQR code created for **{result["bank"]}** account **••••{result["account_no"][-4:]}**{amount}{info}. '
            'Scan it with any banking app and confirm the recipient name before paying.\n\n'
            f'![VietQR]({result["image"]})')


TRANSFER_HINTS = {
    'INSUFFICIENT_FUNDS': 'Your balance is lower than this amount.',
    'RECIPIENT_NOT_FOUND': 'Check the NovaBank account ID.',
    'SAME_ACCOUNT': 'You cannot transfer to the same account.',
    'UNKNOWN_BANK': 'Check the bank name (e.g. Vietcombank, VCB, MB, Techcombank).',
    'INVALID_ACCOUNT': 'Other banks use numeric account numbers.',
}


def render_result(request: BankingRequest, result: dict) -> str:
    if request.tool == 'create_transfer':
        if 'error' in result:
            hint = TRANSFER_HINTS.get(result['reason_code'], 'Please try again from the Transfer screen.')
            return f'I could not prepare this transfer ({result["reason_code"]}). {hint} No money was moved.'
        account = result['to_account'] if result['to_bank'] == 'NovaBank' else '••••' + result['to_account'][-4:]
        # The chat UI turns the TRF reference into a "Review & confirm" button.
        return (f'I prepared a transfer of **{vnd(result["amount_vnd"])}** to **{result["to_bank"]}** account **{account}**. '
                f'Nothing has been sent yet: review the recipient and confirm with the OTP sent to your phone. '
                f'Reference **{result["transfer_id"]}**.')
    if result.get('error') == 'TOOL_FAILED':
        hint = 'Check the bank name (e.g. Vietcombank, VCB, MB, Techcombank).' if result['reason_code'] == 'UNKNOWN_BANK' \
            else 'The VietQR service did not respond; please try again shortly.'
        return f'I could not create the VietQR code ({result["reason_code"]}). {hint}'
    if 'error' in result:
        return f'Request blocked ({result["reason_code"]}). No data was returned and no tool was executed for this request.'
    if request.tool == 'create_vietqr':
        return render_qr(result)
    if request.tool == 'get_recent_transactions':
        lines = [f'• {t["date"]} · {t["description"]} · **{"+" if t["direction"] == "in" else "-"}{vnd(t["amount_vnd"])}** · {t["status"]}'
                 for t in result['transactions']]
        return 'Your recent demo transactions:\n' + '\n'.join(lines)
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
