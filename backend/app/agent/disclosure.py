"""Field minimization and bank-owned answer checks; never an LLM decision."""
import re
from ..faq import fold

REFUSAL = 'I cannot display unsolicited or another customer\'s account details. Please use your banking screens for authorized information.'
PAYMENT_BALANCE = re.compile(r'\b(?:balance|balances|so du|available funds|how much money)\b')
CARD = re.compile(r'\b(?:card|cards|credit|debit|the tin dung|the ghi no|du no|no the)\b')
SAVINGS = re.compile(r'\b(?:savings|saving|deposit|deposits|tiet kiem|tien gui)\b')
DEBT = re.compile(r'\b(?:debt|owe|owed|owing|du no|no the|con no|outstanding balance|outstanding card balance|outstanding credit balance)\b')
AVAILABLE = re.compile(r'\b(?:available|remaining|left|con lai|kha dung)\b')
BALANCE = re.compile(r'\b(?:balance|balances|so du|available funds|how much money|debt|owe|outstanding|du no|no the|principal|tien goc)\b')
ACCOUNT = re.compile(r'\b(?:account|accounts|tai khoan|iban|transfer|chuyen|pay|thanh toan)\b')
PRIVATE_FIELDS = frozenset(('email', 'phone', 'owner_id', 'user_id', 'holder_name'))
FINANCIAL_FIELDS = {
    'balance_vnd': 'payment_balance', 'total_balance_vnd': 'payment_balance',
    'payment_balance_vnd': 'payment_balance', 'available_balance_vnd': 'payment_balance',
    'balance_after_vnd': 'payment_balance', 'balance_before_vnd': 'payment_balance',
    'ledger_balance_vnd': 'payment_balance', 'available_funds_vnd': 'payment_balance',
    'outstanding_vnd': 'card_debt', 'outstanding_balance_vnd': 'card_debt',
    'credit_debt_vnd': 'card_debt', 'debt_vnd': 'card_debt', 'amount_due_vnd': 'card_debt',
    'available_credit_vnd': 'card_available', 'remaining_credit_vnd': 'card_available',
    'credit_limit_vnd': 'card_limit',
    'principal_vnd': 'savings_balance', 'savings_principal_vnd': 'savings_balance',
    'savings_balance_vnd': 'savings_balance', 'total_savings_vnd': 'savings_balance',
    'projected_interest_vnd': 'savings_interest', 'paid_interest_vnd': 'savings_interest',
    'earned_interest_vnd': 'savings_interest', 'interest_vnd': 'savings_interest',
}
BALANCE_FIELDS = frozenset(FINANCIAL_FIELDS)
HISTORY = re.compile(r'\b(?:history|transactions?|purchases?|activity|events?|lich su|giao dich|mua hang|hoat dong)\b')
STATUS_ONLY = re.compile(r'\b(?:status (?:of .{0,40} )?only|only (?:the )?status|just (?:the )?status|chi (?:xem )?trang thai)\b')
NUMBER_WORDS = r'one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi|tram|nghin|ngan|trieu|ty'
MONEY = re.compile(r'\d[\d,._\s]*\s*(?:vnd\b|dong\b|d\b|₫)|\d[\d,._]*\s*(?:[kmb]|thousand|million|billion|nghin|ngan|trieu|ty)\b|\b(?:' + NUMBER_WORDS + r')(?:[\s-]+(?:' + NUMBER_WORDS + r')){0,8}\s+(?:vnd|dong)\b|\b(?:' + NUMBER_WORDS + r')\s+(?:hundred|thousand|million|billion|tram|nghin|ngan|trieu|ty)\b')
BARE_FINANCIAL_NUMBER = re.compile(r'\b(?:balance|balances|debt|principal|outstanding|available credit|du no|no the|tien goc|so du)\b\s*(?:(?:is|are|equals|of|your|my|la|cua|ban|toi|value)\s+|[:=*`_~]\s*){0,8}\d')


def financial_classes(intent):
    """Consent is field-specific; a card-status read is not a debt disclosure."""
    text = fold(intent['text'])
    if STATUS_ONLY.search(text):
        return set()
    card = bool(CARD.search(text))
    savings = bool(SAVINGS.search(text) or re.search(r'\bhow much\b.{0,30}\bsaved\b', text))
    explicit_payment = bool(re.search(r'\b(?:payment|checking|current) account\b|\btai khoan thanh toan\b|\bacc-[a-z0-9-]+\b', text))
    explicit_payment |= bool(not savings and re.search(r'\baccount balance\b|\bso du tai khoan\b', text))
    classes = set()
    if card:
        card_balance = re.search(r'\b(?:credit )?card(?: account)? balance\b|\bbalance (?:of|on) (?:my |the )?(?:credit )?card\b', text)
        if DEBT.search(text) or PAYMENT_BALANCE.search(text) and not AVAILABLE.search(text) and (not explicit_payment or card_balance):
            classes.add('card_debt')
        if AVAILABLE.search(text):
            classes.add('card_available')
        if re.search(r'\b(?:limit|han muc)\b', text) and not AVAILABLE.search(text):
            classes.add('card_limit')
    if savings:
        savings_balance = re.search(r'\bsavings? (?:balance|principal|value|total)\b|\b(?:so du tiet kiem|tien goc)\b', text)
        if re.search(r'\b(?:principal|balance|balances|value|total|saved|so du|tien goc|tong tien)\b', text) and (not explicit_payment or savings_balance):
            classes.add('savings_balance')
        if re.search(r'\b(?:earned|accrued|projected|paid) interest\b|\binterest\b.{0,35}\b(?:earn|earned|accrued|projected|paid|receive|pay)\b|\bhow much interest\b|\btien lai\b|\blai (?:da nhan|du kien|tich luy)\b|\blai\b.{0,30}\bbao nhieu\b', text):
            classes.add('savings_interest')
    if PAYMENT_BALANCE.search(text) and (not card and not savings or explicit_payment or re.search(r'\b(?:debit|the ghi no)\b', text)):
        classes.add('payment_balance')
    return classes


def financial_read_tool(intent):
    classes = financial_classes(intent)
    if 'payment_balance' in classes:
        return 'get_account_balance'
    if classes & {'card_debt', 'card_available', 'card_limit'}:
        return 'get_cards'
    if classes & {'savings_balance', 'savings_interest'}:
        return 'get_savings'
    return None


def wants_balance(intent):
    return 'payment_balance' in financial_classes(intent)


def wants_accounts(conn, user_id, intent):
    text = intent['text'].casefold()
    return bool(ACCOUNT.search(fold(text))) or any(row[0].casefold() in text
        for row in conn.execute('SELECT id FROM accounts WHERE owner_id=?', (user_id,)))


def minimize(conn, user, name, result, intent):
    """Keep operational amounts, but disclose balances only for an explicit question."""
    classes = financial_classes(intent) if user.role != 'support' else set()
    history = bool(HISTORY.search(fold(intent['text'])))
    identifiers = wants_accounts(conn, user.id, intent) or user.role != 'customer'
    accounts = {r['id']: r['owner_id'] == user.id for r in conn.execute('SELECT id,owner_id FROM accounts')}

    def visit(value, key=''):
        if isinstance(value, list):
            return [visit(v) for v in value]
        if isinstance(value, dict):
            result = {k: visit(v, k) for k, v in value.items()
                    if k not in PRIVATE_FIELDS and (k not in FINANCIAL_FIELDS or FINANCIAL_FIELDS[k] in classes)
                    and (history or not (name == 'get_cards' and k == 'transactions' or name == 'get_savings' and k == 'events'))
                    and (identifiers or not (k in ('account_id', 'account_no', 'from_account', 'to_account')
                                             or k == 'id' and isinstance(v, str) and v in accounts))}
            if (name == 'get_cards' and value.get('kind') == 'CREDIT' and 'card_available' in classes
                    and type(value.get('credit_limit_vnd')) is int and type(value.get('outstanding_vnd')) is int):
                result['available_credit_vnd'] = max(0, value['credit_limit_vnd'] - value['outstanding_vnd'])
            return result
        if isinstance(value, str) and value and ((value in accounts and not accounts[value])
                or key in ('account_id', 'account_no', 'to_account', 'from_account') and not accounts.get(value, False)):
            return '••••' + value[-4:]
        return value
    return visit(result)


def filter_answer(conn, user_id, intent, answer, *, verified_balance=False):
    """Do not restore a foreign account ID or an unverified balance into model prose."""
    show_accounts = wants_accounts(conn, user_id, intent)
    allowed = financial_classes(intent)
    role = conn.execute('SELECT role FROM users WHERE id=?', (user_id,)).fetchone()
    if role and role[0] == 'support':
        allowed = set()
    wants_balances = 'payment_balance' in allowed
    mentions_balance = 'payment_balance' in financial_classes({'text': answer})
    # Numbers in an operational transfer/purchase are not account/debt balances.
    # Conversely, a private monetary claim is blocked even if the model spells
    # the number out or its value is absent from the payment-account table.
    for fragment in re.split(r'(?<=[.!?;])\s+', fold(answer)):
        claimed = financial_classes({'text': fragment})
        if re.search(r'\b(?:your|my) savings interest\b|\bsavings interest (?:is|:)\b|\btien lai (?:cua ban|la)\b', fragment):
            claimed.add('savings_interest')
        if claimed - allowed and (MONEY.search(fragment) or BARE_FINANCIAL_NUMBER.search(fragment)):
            return REFUSAL
    own = {row[0] for row in conn.execute('SELECT id FROM accounts WHERE owner_id=?', (user_id,))}
    recipients = {row[0] for row in conn.execute('SELECT account_id FROM beneficiaries WHERE owner_id=? UNION SELECT to_account FROM transfers WHERE owner_id=?', (user_id, user_id))}
    if any(account and account not in own and account.casefold() in answer.casefold() for account in recipients):
        return REFUSAL
    for row in conn.execute('SELECT id,owner_id,balance_vnd FROM accounts'):
        owned = row['owner_id'] == user_id
        if row['id'].casefold() in answer.casefold() and (not owned or not show_accounts):
            return REFUSAL
        if not verified_balance and mentions_balance and (not owned or not wants_balances):
            number = str(row['balance_vnd'])
            forms = {number, format(row['balance_vnd'], ','), format(row['balance_vnd'], ',').replace(',', '.')}
            if any(re.search(r'(?<!\d)' + re.escape(value) + r'(?!\d)', answer) for value in forms):
                return REFUSAL
    return answer
