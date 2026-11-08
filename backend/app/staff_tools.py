"""Staff capabilities, selected from the authenticated database role.

Reads mirror the HTTP admin routes' permissions, so the agent never exceeds the caller.
Writes are proposals only: an admin approves them in the app and the role is checked again then.
"""
import difflib
import json
import re
from typing import Literal
from fastapi import HTTPException
from pydantic import Field, model_validator
from .auth import ROLE_PERMISSIONS
from .identity_schemas import IdentityInput
from .banking_workflow import affirmative_action
from .faq import fold
from .routes_admin import Settings, UserState, apply_account_state, apply_settings, apply_user_state, overview_counts
from .routes_support import Assignment, apply_assignment, post_reply


class TicketArgs(IdentityInput):
    ticket_id: str = Field(min_length=3, max_length=80)


class TransactionsArgs(IdentityInput):
    limit: int = Field(default=10, ge=1, le=50)
    mask: bool = True


class ListArgs(IdentityInput):
    limit: int = Field(default=20, ge=1, le=50)


TicketStatus = Literal['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']


class TicketListArgs(IdentityInput):
    status: TicketStatus | None = None
    limit: int = Field(default=20, ge=1, le=50)


class CustomerArgs(IdentityInput):
    user_id: str | None = Field(default=None, min_length=2, max_length=100)
    ticket_id: str | None = Field(default=None, min_length=3, max_length=80)

    @model_validator(mode='after')
    def one_target(self):
        if (self.user_id is None) == (self.ticket_id is None):
            raise ValueError('Give either user_id or ticket_id.')
        return self


class TicketReplyArgs(IdentityInput):
    ticket_id: str = Field(min_length=3, max_length=80)
    body: str = Field(min_length=1, max_length=2000)


class TicketStatusArgs(IdentityInput):
    ticket_id: str = Field(min_length=3, max_length=80)
    status: TicketStatus
    assigned_to: str | None = Field(default=None, max_length=64)


class AccountStatusArgs(IdentityInput):
    account_id: str = Field(min_length=3, max_length=100)
    # Closing is irreversible, so it stays a manual console action.
    status: Literal['ACTIVE', 'FROZEN']


class CustomerUpdateArgs(UserState):
    user_id: str = Field(min_length=2, max_length=100)

    @model_validator(mode='after')
    def one_change(self):
        if self.status is None and self.kyc_status is None:
            raise ValueError('Choose a status or kyc_status change.')
        return self


class SettingsChangeArgs(Settings):
    @model_validator(mode='after')
    def one_change(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError('Choose at least one setting to change.')
        return self


class ReconcileArgs(IdentityInput):
    pass


READS = {'list_tickets': 'support:read', 'read_ticket': 'support:read',
         'get_customer_summary': 'admin:audit:read', 'list_failed_transfers': 'admin:transactions:read',
         'get_user_count': 'settings:write', 'list_transactions': 'admin:transactions:read',
         'get_bank_overview': 'admin:audit:read', 'list_customers': 'admin:audit:read',
         'list_accounts': 'admin:audit:read', 'get_bank_settings': 'admin:audit:read',
         'list_audit_events': 'admin:audit:read'}
PROPOSALS = {'propose_ticket_reply': 'support:write', 'propose_ticket_status': 'support:write',
             'propose_account_status': 'settings:write', 'propose_customer_update': 'settings:write',
             'propose_settings_change': 'settings:write', 'propose_reconciliation': 'settings:write'}
PERMISSIONS = {**READS, **PROPOSALS}
WRITE_INTENT = re.compile(r'\b(freeze|unfreeze|lock|unlock|disable|enable|activate|verify|kyc|set|change|update|raise|lower|'
                          r'reconcile|reconciliation|turn|reply|respond|answer|resolve|close|reopen|assign|handle|'
                          r'khóa|khoá|mở|đổi|cập nhật|đặt|bật|tắt|xác minh|đối soát|trả lời|phản hồi|giải quyết|xử lý|đóng|phân công|giao)\b', re.I)


def allowed(role):
    permissions = ROLE_PERMISSIONS.get(role, frozenset())
    return {tool for tool, permission in PERMISSIONS.items() if permission in permissions}


def offered(role, text):
    # Write proposals are only offered when the staff message itself asks for a change.
    names = allowed(role)
    return names if affirmative_action(text, fold(WRITE_INTENT.pattern) + r'|run') else names - PROPOSALS.keys()


def bind(content):
    text = content.lower()
    ticket = re.search(r'\bTKT-[A-Za-z0-9]+\b', content, re.I)
    if ticket:
        status = 'CLOSED' if re.search(r'\b(close|đóng)\b', text) else 'RESOLVED' if re.search(r'\b(resolve|giải quyết)\b', text) else None
        if status and not re.search(r'\b(reply|respond|answer|trả lời|phản hồi)\b', text):
            return {'text': content, 'tool': 'propose_ticket_status', 'arguments': {'ticket_id': ticket.group().upper(), 'status': status}}
        if re.search(r'\b(reply|respond|answer|trả lời|phản hồi)\b', text):
            return {'text': content, 'tool': 'propose_ticket_reply', 'arguments': {'ticket_id': ticket.group().upper()}}
        return {'text': content, 'tool': 'read_ticket', 'arguments': {'ticket_id': ticket.group().upper()}}
    account = re.search(r'\bACC-[A-Za-z0-9-]+\b', content, re.I)
    if account and re.search(r'\b(unfreeze|unlock|mở)\b', text):
        return {'text': content, 'tool': 'propose_account_status', 'arguments': {'account_id': account.group().upper(), 'status': 'ACTIVE'}}
    if account and re.search(r'\b(freeze|lock|khóa|khoá)\b', text):
        return {'text': content, 'tool': 'propose_account_status', 'arguments': {'account_id': account.group().upper(), 'status': 'FROZEN'}}
    if re.search(r'reconcil|đối soát', text) and WRITE_INTENT.search(text):
        return {'text': content, 'tool': 'propose_reconciliation', 'arguments': {}}
    for pattern, name in ((r'audit|nhật ký', 'list_audit_events'), (r'overview|dashboard|tổng quan', 'get_bank_overview'),
                          (r'setting|limit|fee|hạn mức|phí', 'get_bank_settings'), (r'account|tài khoản', 'list_accounts'),
                          (r'customer|khách', 'list_customers'), (r'user', 'get_user_count'), (r'transaction|giao dịch', 'list_transactions')):
        if re.search(pattern, text):
            return {'text': content, 'tool': name, 'arguments': {}}
    return {'text': content, 'tool': 'list_tickets', 'arguments': {}}


def execute(conn, user, name, args, intent, bound=True):
    if (bound and name not in allowed(user.role)) or name in PROPOSALS:
        raise HTTPException(403, 'ROLE_NOT_PERMITTED')
    if name == 'get_user_count':
        return {'count': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]}
    if name == 'list_tickets':
        rows = conn.execute('''SELECT t.id,t.subject,t.status,t.created_at,a.assigned_to,COALESCE(a.category,'GENERAL') AS category
            FROM support_tickets t LEFT JOIN ticket_assignments a ON a.ticket_id=t.id WHERE ? IS NULL OR t.status=?
            ORDER BY t.created_at DESC LIMIT ?''', (args.get('status'), args.get('status'), args['limit']))
        return {'items': [dict(r) for r in rows], 'trust_level': 'untrusted'}
    if name == 'get_customer_summary':
        if args.get('ticket_id'):
            # Owner IDs are pseudonymized for the model; resolving by ticket keeps the lookup exact.
            owner = conn.execute('SELECT owner_id FROM support_tickets WHERE id=?', (args['ticket_id'],)).fetchone()
            if not owner:
                raise HTTPException(404, 'TICKET_NOT_FOUND')
            args = {**args, 'user_id': owner[0]}
        person = conn.execute('''SELECT u.id,u.role,u.status,u.created_at,COALESCE(p.kyc_status,'UNVERIFIED') AS kyc_status
            FROM users u LEFT JOIN customer_profiles p ON p.user_id=u.id WHERE u.id=?''', (args['user_id'],)).fetchone()
        if not person:
            raise HTTPException(404, 'CUSTOMER_NOT_FOUND')
        return {**dict(person),
                'accounts': [dict(r) for r in conn.execute('SELECT id,status,balance_vnd FROM accounts WHERE owner_id=? ORDER BY id', (args['user_id'],))],
                'tickets': [dict(r) for r in conn.execute('SELECT id,status,created_at FROM support_tickets WHERE owner_id=? ORDER BY created_at DESC LIMIT 10', (args['user_id'],))],
                'failed_transfers': conn.execute('''SELECT COUNT(*) FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
                    WHERE t.owner_id=? AND (t.status='FAILED' OR s.status='FAILED')''', (args['user_id'],)).fetchone()[0]}
    if name == 'list_failed_transfers':
        return {'items': [dict(r) for r in conn.execute('''SELECT t.id,t.owner_id,t.from_account,t.amount_vnd,t.status,s.status AS settlement_status,
            s.failure_reason,t.created_at FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
            WHERE t.status='FAILED' OR s.status='FAILED' ORDER BY t.created_at DESC LIMIT ?''', (args['limit'],))]}
    if name == 'read_ticket':
        if bound and args['ticket_id'].casefold() not in intent['text'].casefold():
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
        row = conn.execute('''SELECT t.id,t.owner_id,t.subject,t.description,t.status,t.created_at,a.assigned_to,COALESCE(a.category,'GENERAL') AS category
            FROM support_tickets t LEFT JOIN ticket_assignments a ON a.ticket_id=t.id WHERE t.id=?''', (args['ticket_id'],)).fetchone()
        if not row:
            raise HTTPException(404, 'TICKET_NOT_FOUND')
        thread = [dict(r) for r in conn.execute('''SELECT CASE WHEN m.author_id=? THEN 'customer' ELSE 'staff' END AS author,m.body,m.created_at
            FROM ticket_messages m WHERE m.ticket_id=? ORDER BY m.created_at,m.rowid LIMIT 30''', (row['owner_id'], args['ticket_id']))]
        text = ' '.join([row['subject'], row['description'], *(m['body'] for m in thread)])
        # Records and policy ride along with the ticket so a reply never has to guess them.
        customer = ' '.join([row['subject'], row['description'], *(m['body'] for m in thread if m['author'] == 'customer')])
        return {**dict(row), 'messages': thread, 'trust_level': 'untrusted',
                'customer_records': customer_facts(conn, row['owner_id']), 'bank_policy': policy_for(conn, text),
                'reply_language': language_of(customer),
                'note': 'Only customer_records and bank_policy are known. Causes, delays and outcomes not shown there are unknown: '
                        'do not guess them; say the team will check and what the customer can do now.'}
    if name == 'get_bank_overview':
        return overview_counts(conn)
    if name == 'list_customers':
        # Identifiers and states only; names, emails and credentials stay out of the model.
        return {'items': [dict(r) for r in conn.execute('''SELECT u.id,u.role,u.status,COALESCE(p.kyc_status,'UNVERIFIED') AS kyc_status
            FROM users u LEFT JOIN customer_profiles p ON p.user_id=u.id ORDER BY u.id LIMIT ?''', (args['limit'],))],
                'total': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]}
    if name == 'list_accounts':
        return {'items': [dict(r) for r in conn.execute('SELECT id,owner_id,status,balance_vnd FROM accounts ORDER BY id LIMIT ?', (args['limit'],))],
                'total': conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]}
    if name == 'get_bank_settings':
        return {r['key']: json.loads(r['value_json']) for r in conn.execute('SELECT key,value_json FROM bank_settings')}
    if name == 'list_audit_events':
        return {'items': [dict(r) for r in conn.execute('SELECT action,owner_id,resource_id,reason_code,created_at FROM banking_audit ORDER BY created_at DESC,rowid DESC LIMIT ?', (args['limit'],))],
                'trust_level': 'untrusted'}
    # Masking is mandatory; a model cannot turn it off by passing mask=false.
    if not args['mask']:
        raise HTTPException(403, 'MASK_REQUIRED')
    return {'items': [dict(r) for r in conn.execute('SELECT id,amount_vnd,direction,status,date FROM transactions ORDER BY date DESC LIMIT ?', (args['limit'],))], 'masked': True}


def numbers(text):
    # shortcut: plain digits only ("5,000" or "5000"); "5k"/"5 triệu" are not understood, add units if staff ask.
    return {int(re.sub(r'[.,_]', '', n)) for n in re.findall(r'\d[\d.,_]*\d|\d', text)}


# A reply cannot report account actions: none happen as part of answering a ticket.
DONE = (r'(?:frozen|froze|unfrozen|unfroze|locked|blocked|disabled|suspended|secured|refunded|reversed|cancell?ed|replaced|'
        r'reissued|reset|fixed|processed|investigated|reviewed)')
DONE_VI = r'(?:chặn|khóa|khoá|mở khóa|hoàn tiền|hoàn trả|kiểm tra|xử lý|giải quyết|điều tra|xem xét|hủy|huỷ|đặt lại|bảo vệ)'
CLAIMED_ACCOUNT_ACTION = re.compile(
    r"\b(?:we|i)(?: have|'ve)?\s+(?:already\s+)?" + DONE + r"\b|\bclosed your account\b"
    r"|\b(?:has|have) (?:now |already )?been " + DONE + r"\b"
    r"|\b(?:appears|seems) to be (?:a )?(?:legitimate|genuine|authori[sz]ed)\b|\bis not (?:a )?fraud"
    r"|(?:chúng tôi|novabank|ngân hàng)\s+đã\s+(?:tiến hành\s+)?" + DONE_VI + r"|đã được\s+" + DONE_VI, re.I)


def fill_name_placeholders(body):
    """Small models write letter templates; swap name placeholders for neutral words. Other placeholders still fail."""
    body = body.strip().strip('{}').strip()  # stray JSON braces from the model's tool call
    body = re.sub(r'\s*\[KB-[^\]]*\]', '', body)  # knowledge citations are for staff, not the customer
    # Small models sometimes greet the assignee ("Chào Support") instead of the customer.
    body = re.sub(r'(?i)^(hello|hi|dear|xin chào|chào)\s*,?\s*(?:support|admin|operations|auditor)\b\s*[,.!]?\s*', r'\1,\n\n', body)
    body = re.sub(r'(?i)\b(?:dear|hi|hello)\s*,?\s*\[[^\]]*(?:name|customer)[^\]]*\]\s*[,.!]?\s*', 'Hello,\n\n', body)
    body = re.sub(r'(?i)\[\s*(?:your|agent|staff|support)[^\]]*name[^\]]*\]', 'NovaBank Support', body)
    return re.sub(r'(?i)\s*\[\s*customer(?:\'s)?\s*name\s*\]', '', body)


def repair_ticket_id(args, text):
    """Fix a copy slip (small models drop repeated digits) of the single ticket ID the staff named.

    A clearly different ID (another ticket, e.g. named inside injected text) is left alone and fails binding.
    """
    named = {t.upper() for t in re.findall(r'\bTKT-[A-Za-z0-9]+\b', text, re.I)}
    given = str(args.get('ticket_id') or '').upper()
    if len(named) != 1 or not given or given in named:
        return args
    target = next(iter(named))
    if difflib.SequenceMatcher(None, given, target).ratio() >= 0.8:
        return {**args, 'ticket_id': target}
    return args


def customer_facts(conn, owner):
    return {'accounts': [dict(r) for r in conn.execute('SELECT id,status,balance_vnd FROM accounts WHERE owner_id=? ORDER BY id', (owner,))],
            'cards': [dict(r) for r in conn.execute('SELECT kind,status,credit_limit_vnd,outstanding_vnd FROM cards WHERE owner_id=? ORDER BY id', (owner,))],
            'recent_transfers': [dict(r) for r in conn.execute(
                'SELECT t.id,t.amount_vnd,t.status,s.status AS settlement_status,s.failure_reason,t.created_at FROM transfers t '
                'LEFT JOIN interbank_settlements s ON s.transfer_id=t.id WHERE t.owner_id=? ORDER BY t.created_at DESC LIMIT 5', (owner,))]}


def policy_for(conn, text, limit=2):
    """Approved knowledge sharing the most words with the ticket, so replies quote bank policy instead of guessing."""
    words = set(re.findall(r'\w{4,}', text.lower()))
    docs = conn.execute("SELECT id,title,content FROM knowledge_documents WHERE status='PUBLISHED' AND trust_level='approved'").fetchall()
    scored = sorted(((len(words & set(re.findall(r'\w{4,}', (d['title'] + ' ' + d['content']).lower()))), d['id']) for d in docs), reverse=True)
    keep = {i for score, i in scored[:limit] if score}
    return [{'id': d['id'], 'title': d['title'], 'text': d['content']} for d in docs if d['id'] in keep]


def ticket_facts(conn, ticket_id):
    """(Numbers a reply may state, the customer's own words). Facts: the thread, the owner's records, the policy shown."""
    row = conn.execute('SELECT id,owner_id,subject,description FROM support_tickets WHERE id=?', (ticket_id,)).fetchone()
    messages = conn.execute('SELECT body,author_id FROM ticket_messages WHERE ticket_id=?', (ticket_id,)).fetchall()
    text = ' '.join([row['subject'], row['description'], *(m[0] for m in messages)])
    customer = ' '.join([row['subject'], row['description'], *(m[0] for m in messages if m[1] == row['owner_id'])])
    facts = text + json.dumps(customer_facts(conn, row['owner_id'])) + json.dumps(policy_for(conn, text))
    # IDs and timestamps are not facts a reply can quote; their digits would make any small number look grounded.
    return re.sub(IDS.pattern + r'|"\d{4}-\d\d-\d\dT[^"]*"', ' ', facts), customer


IDS = re.compile(r'\b[A-Z]{2,}-[A-Za-z0-9-]+\b')


def mentioned(value, text):
    return re.search(r'(?<![\w-])' + re.escape(value) + r'(?![\w-])', text, re.I) is not None


def require_choice(text, value, patterns):
    choices = {choice for choice, pattern in patterns.items() if re.search(pattern, fold(text))}
    if choices != {value}:
        raise HTTPException(403, 'USER_INTENT_MISMATCH')


SECRET = re.compile(r'\b(otp|password|passcode|pin|cvv|recovery code|mật khẩu|mã xác (thực|nhận)|mã otp)\b', re.I)
# "enter"/"nhập" are left out on purpose: "enter a new password", "đăng nhập" (sign in) are normal instructions.
ASKS = re.compile(r"\b(send|share|provide|give|tell|confirm|reply with|read out|what is|what's|gửi|cung cấp|cho biết|đọc)\b", re.I)
VIETNAMESE = re.compile('[ăâđêôơưàáạảãầấậẩẫằắặẳẵèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]', re.I)


def language_of(text):
    return 'Vietnamese' if len(VIETNAMESE.findall(text)) >= 2 else 'English'
NEGATED = re.compile(r"\b(never|not|don't|do not|won't|will not|không bao giờ|không|đừng|chớ)\b", re.I)


def unsafe_reply(body):
    """Bank policy: staff never send links or ask for credentials. Warnings ("we never ask for your OTP") stay allowed."""
    # shortcut: sentence-level keyword check, not semantic; an admin still reviews every draft before it is sent.
    if re.search(r'https?://|www\.', body, re.I):
        return True
    # Mentioning a credential is fine ("click Forgot password"); asking for one is not.
    return any(SECRET.search(s) and ASKS.search(s) and not NEGATED.search(s) for s in re.split(r'[.!?\n]+', body))


def bind_proposal(conn, name, args, text):
    """Anchor every proposed target and value to the staff member's own latest message."""
    if not affirmative_action(text, fold(WRITE_INTENT.pattern) + r'|run'):
        raise HTTPException(403, 'USER_INTENT_REQUIRED')
    if name in ('propose_ticket_reply', 'propose_ticket_status'):
        if not mentioned(args['ticket_id'], text):
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
        if not conn.execute('SELECT 1 FROM support_tickets WHERE id=?', (args['ticket_id'],)).fetchone():
            raise HTTPException(404, 'TICKET_NOT_FOUND')
        if name == 'propose_ticket_reply' and unsafe_reply(args['body']):
            raise HTTPException(403, 'UNSAFE_REPLY')
        if name == 'propose_ticket_reply':
            args = {**args, 'body': fill_name_placeholders(args['body'])}
        # [Name] templates, and privacy tokens the model copied or mangled (<NAME_1, <PHONE_1>) instead of real text.
        if name == 'propose_ticket_reply' and re.search(r'\[[^\]]{2,40}\]|<\s*(?:NAME|PHONE|EMAIL|ACCOUNT|USER|ID)(?![a-z])', args['body'], re.I):
            raise HTTPException(422, 'REPLY_HAS_PLACEHOLDER')
        if name == 'propose_ticket_reply':
            owner = conn.execute('SELECT owner_id FROM support_tickets WHERE id=?', (args['ticket_id'],)).fetchone()[0]
            owned = {r[0].upper() for r in conn.execute('SELECT id FROM accounts WHERE owner_id=?', (owner,))}
            # Ticket text may name other customers' accounts (injection); a reply never discloses or acts on them.
            if any(a.upper() not in owned for a in re.findall(r'\bACC-[A-Za-z0-9-]+\b', args['body'])):
                raise HTTPException(422, 'REPLY_MENTIONS_OTHER_ACCOUNT')
            if claim := CLAIMED_ACCOUNT_ACTION.search(args['body']):
                raise HTTPException(422, 'REPLY_CLAIMS_UNDONE_ACTION', headers={'x-offending': repr(claim.group())})
            # Every number (amount, balance, delay) must come from the ticket, the customer's records or bank policy.
            facts, customer_text = ticket_facts(conn, args['ticket_id'])
            stated = re.sub(r'(?m)^\s*\d+[.)]\s|' + IDS.pattern, ' ', args['body'])  # list markers and IDs are not claims
            invented = sorted(numbers(stated) - numbers(facts))
            if re.search(r'\$|\bUSD\b', args['body']) or invented:
                raise HTTPException(422, 'REPLY_UNGROUNDED_FACT', headers={'x-offending': 'the numbers ' + ', '.join(map(str, invented)) if invented else 'the $ / USD amounts'})
            if language_of(args['body']) != language_of(customer_text):
                raise HTTPException(422, 'REPLY_WRONG_LANGUAGE')
        if args.get('assigned_to') and not mentioned(args['assigned_to'], text):
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
        if name == 'propose_ticket_status':
            require_choice(text, args['status'], {'RESOLVED': r'\b(?:resolve|resolved|giai quyet)\b',
                'CLOSED': r'\b(?:close|closed)\b|\bdong (?:ticket|yeu cau|lai)\b',
                'IN_PROGRESS': r'\b(?:in[ _]progress|working on|dang xu ly)\b',
                'OPEN': r'\b(?:reopen|re-open|mo lai)\b'})
    elif name == 'propose_account_status':
        if not mentioned(args['account_id'], text):
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
        if not conn.execute('SELECT 1 FROM accounts WHERE id=?', (args['account_id'],)).fetchone():
            raise HTTPException(404, 'ACCOUNT_NOT_FOUND')
        requested = bind(text)
        if requested['tool'] != name or requested['arguments'].get('status') != args['status']:
            raise HTTPException(403, 'USER_INTENT_MISMATCH')
    elif name == 'propose_customer_update':
        if not mentioned(args['user_id'], text):
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND role='customer'", (args['user_id'],)).fetchone():
            raise HTTPException(404, 'CUSTOMER_NOT_FOUND')
        if 'status' in args:
            require_choice(text, args['status'], {'ACTIVE': r'\b(?:activate|enable|active)\b',
                'DISABLED': r'\b(?:disable|disabled|deactivate)\b'})
        if 'kyc_status' in args:
            require_choice(text, args['kyc_status'], {'VERIFIED': r'\b(?:verify|verified|xac minh)\b',
                'UNVERIFIED': r'\bunverified\b'})
    elif name == 'propose_settings_change':
        # A mentioned number is not authority to use it for another setting.
        labels = {
            'transfer_fee_vnd': r'transfer_fee_vnd|(?:transfer\s+)?fee|phi(?:\s+chuyen\s+tien)?',
            'transfer_limit_vnd': r'transfer_limit_vnd|(?:per[- ]transfer|transfer)\s+limit|han muc moi giao dich',
            'daily_limit_vnd': r'daily_limit_vnd|daily\s+limit|han muc ngay',
        }
        for key, value in args.items():
            if key == 'agent_enabled':
                if not re.search(r'\b(assistant|agent|nova|trợ lý)\b', text, re.I):
                    raise HTTPException(403, 'USER_INTENT_REQUIRED')
                require_choice(text, value, {True: r'\b(?:enable|enabled|activate|bat)\b|\bturn\b.{0,35}\bon\b',
                    False: r'\b(?:disable|disabled|deactivate|tat)\b|\bturn\b.{0,35}\boff\b'})
            else:
                match = re.search(r'\b(?:' + labels[key] + r')\b\s*(?:to|is|=|:|la|thanh)?\s*(\d[\d,._]*)\b', fold(text))
                if not match or int(re.sub(r'[.,_]', '', match.group(1))) != value:
                    raise HTTPException(403, 'USER_INTENT_MISMATCH')
    elif name == 'propose_reconciliation':
        if not re.search(r'reconcil|đối soát', text, re.I):
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
    return args


def apply(conn, user, name, args):
    """Run an approved proposal through the same code path as the admin console."""
    if name not in allowed(user.role):
        raise HTTPException(403, 'ROLE_NOT_PERMITTED')
    if name == 'propose_ticket_reply':
        return post_reply(conn, user, args['ticket_id'], args['body'])
    if name == 'propose_ticket_status':
        current = conn.execute('SELECT assigned_to FROM ticket_assignments WHERE ticket_id=?', (args['ticket_id'],)).fetchone()
        # Keep the existing assignee unless the staff member named a new one.
        assignee = args.get('assigned_to') or (current[0] if current else None)
        return apply_assignment(conn, user, args['ticket_id'], Assignment(status=args['status'], assigned_to=assignee))
    if name == 'propose_account_status':
        return apply_account_state(conn, user, args['account_id'], AccountStatusArgs(**args))
    if name == 'propose_customer_update':
        return apply_user_state(conn, user, args['user_id'], UserState(**{k: v for k, v in args.items() if k != 'user_id'}))
    if name == 'propose_settings_change':
        return {'message': 'Settings updated.', 'settings': apply_settings(conn, user, Settings(**args))}
    raise HTTPException(403, 'TOOL_NOT_ALLOWED')
