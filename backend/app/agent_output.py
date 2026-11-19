"""Bank-owned filtering shared by live previews and persisted final answers."""
import json
import re
from .auth_crypto import decrypt_secret

# The assistant never executes money movement or account changes itself, so a claim that it did is false.
FALSE_DONE = re.compile(
    r"(?i)\b(?:(?:has|have) been (?:successfully )?(?:processed|sent|paid|transferred|submitted|created|executed|made)"
    r"|processed successfully|(?:is|was) now (?:complete|completed|successful|paid|sent)"
    r"|I(?: have|'ve)? (?:successfully |just )?(?:sent|paid|transferred|processed|created|submitted|executed|completed)\b)")
# Documents can describe completed payments. Only the assistant claiming authorship
# is a false completion on a document turn.
FIRST_PERSON_DONE = re.compile(
    r"\b(?:I|we)(?: have|['’]ve)?\s+(?:(?:just|already|successfully)\s+)*"
    r"(?:sent|paid|transferred|processed|created|submitted|executed|completed|confirmed|approved|made|filed|opened)\b"
    r"|\b(?:tôi|mình|chúng tôi)\s+(?:đã|vừa)\s+(?:chuyển|gửi|thanh toán|xác nhận|tạo)\b", re.I)
# Detect a claim about one specific transfer, transaction or ticket (EN/VI).
# Specific = the assistant speaks in the first person, the user's own item, or a concrete amount. Conditional or
# general rules (if/once/when/unless/nếu/khi) are policy text, not claims.
# Without a bound status-read intent, detection still depends on the wording of the answer.
STATUS_SPECIFIC = re.compile(r"\bI(?:'ve| have)?\b|(?i:\b(?:tôi|mình) đã\b|\byour (?:\w+ )?(?:transfer|payment|transaction|ticket|request|refund)s?\b"
                             r"|\bcủa bạn\b|\d[\d.,]*\s*(?:VND|₫|đ)\b)")
CONDITIONAL = re.compile(r'(?i)\b(?:if|once|when|unless|nếu|khi)\b')
STATUS_SUBJECT = re.compile(r'(?i)\b(?:transfer|payment|transaction|ticket|money|funds|refund)s?\b|\d[\d.,]*\s*(?:VND|₫|đ)\b'
                            r'|\b(?:chuyển|giao dịch|thanh toán|phiếu|tiền|hoàn tiền)\b')
STATUS_CLAIM = re.compile(
    r"(?i)\b(?:has|have|had) been\b|\b(?:was|were) (?:successfully |already )?(?:\w+ed|sent|paid|done|made)\b"
    r"|\b(?:is|are) (?:now|being|already)\b|\bconfirmed\b|\bsuccessful(?:ly)?\b|\bwent through\b|\bon (?:its|the) way\b"
    r"|\bI(?:'ve| have)? (?:successfully |just |already )?(?:sent|paid|transferred|processed|created|submitted|executed|completed|confirmed|approved|made|filed|opened)\b"
    r"|\b(?:đã|đang được|vừa)\b|\bthành công\b|\bhoàn tất\b|\bxác nhận\b")
STATUS_READS = ('get_transaction_status', 'get_recent_transactions', 'get_support_tickets')


# Transaction topics (EN/VI, with or without diacritics). On a turn whose bound message never raised money, an answer may
# not state the status of a transaction: one sentence with a topic word and a status word is replaced.
# shortcut: a status sentence with no topic word ("Done, it went through.") or no status word passes, and a policy sentence
# with both ("...that has been scanned...payment") is replaced; upgrade with a server-side classifier if either is abused.
TOPIC = re.compile(r'(?i)\b(?:transfer\w*|payments?|pay|paid|transactions?|money|funds?|refund\w*|tickets?|support requests?)\b'
                   r'|\b(?:chuyển|chuyển tiền|chuyển khoản|thanh toán|giao dịch|tiền|hoàn tiền|phiếu hỗ trợ)\b'
                   r'|\b(?:chuyen tien|chuyen khoan|thanh toan|giao dich|hoan tien|phieu ho tro)\b')
# The user raises a money topic in more words than an answer may (spending, bills, recipients...). "card" is left out on
# purpose: "How do I change my card PIN?" must stay off-topic.
USER_TOPIC = re.compile(TOPIC.pattern + r'|\b(?:spend\w*|spent|bills?|recipients?|beneficiar\w*|limits?|balances?|accounts?)\b'
                        r'|\b(?:chi tiêu|chi tieu|hóa đơn|hoá đơn|hoa don|người nhận|nguoi nhan|hạn mức|han muc|số dư|so du|tài khoản|tai khoan)\b')


def sentences(answer):
    return re.split(r'(?<=[.!?])\s+|\n', answer)


def opens_topic(user_text, answer):
    # No STATUS_SPECIFIC and no conditional exemption here: the user never asked, so any status sentence is a claim.
    return not USER_TOPIC.search(user_text) and any(
        (TOPIC.search(s) or STATUS_SUBJECT.search(s)) and STATUS_CLAIM.search(s) for s in sentences(answer))


def claims_status(answer):
    return any(STATUS_SUBJECT.search(s) and STATUS_CLAIM.search(s) and STATUS_SPECIFIC.search(s) and not CONDITIONAL.search(s)
               for s in sentences(answer))


NOT_DONE = ("The assistant has not sent, paid or changed anything. I can't confirm a payment or ticket status "
            "from this chat. Check Activity, or ask about a specific transaction ID.")


def status_facts(conn, run, *, single_lookup_only=False):
    """Newest observation per record, drawn only from this run's allowed bank reads."""
    from .agent.guard import TOKEN
    facts = {}
    calls = conn.execute(
        """SELECT name,result_json FROM agent_calls WHERE run_id=? AND decision='ALLOW'
           AND name IN (?,?,?) ORDER BY ordinal DESC""", (run['id'], *STATUS_READS))
    for tool, payload in calls:
        if single_lookup_only and tool != 'get_transaction_status':
            continue
        result = json.loads(payload)
        items = [result] if tool == 'get_transaction_status' else result.get('items', [])
        for item in items:
            identifier, status = item.get('id'), item.get('status')
            if not isinstance(identifier, str) or identifier in facts:
                continue
            # A random bank ID can contain a digit run already replaced by a privacy alias.
            display_id = TOKEN.sub('*****', identifier)
            if tool == 'get_support_tickets':
                if re.fullmatch(r'TKT-[A-Za-z0-9*-]+', display_id) and status in ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'):
                    facts[identifier] = {'id': display_id, 'status': status, 'tool': tool}
                continue
            amount, direction, date = item.get('amount_vnd'), item.get('direction'), item.get('date')
            if (re.fullmatch(r'TX-[A-Za-z0-9*-]+', display_id) and status in ('COMPLETED', 'PENDING', 'FAILED')
                    and type(amount) is int and direction in ('in', 'out')
                    and isinstance(date, str) and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date)):
                if re.fullmatch(r'TX-[A-Fa-f0-9]{32}', display_id):
                    display_id = identifier[:11] + '*****' + identifier[-7:]
                facts[identifier] = {'id': display_id, 'status': status, 'tool': tool,
                                     'amount': amount, 'direction': direction, 'date': date}
    if single_lookup_only and len(facts) != 1:
        return []
    return list(facts.values())


def render_status(facts):
    lines = []
    transaction_count = 0
    for fact in facts:
        if fact['tool'] == 'get_support_tickets':
            lines.append(f"Ticket {fact['id']}: {fact['status']}.")
        elif transaction_count < 5:
            direction = 'outgoing' if fact['direction'] == 'out' else 'incoming'
            lines.append(f"Transaction {fact['id']}: {fact['status']} · {fact['amount']:,} VND · {direction} · {fact['date']}.")
            transaction_count += 1
    if transaction_count > 1 or any(f['tool'] == 'get_recent_transactions' for f in facts):
        lines.append('See Activity for the full list.')
    return '\n'.join(lines)


# Staff runs: the bank applies changes only after approval, so "marked as resolved" / "froze the account" is false.
STAFF_FALSE_DONE = re.compile(
    r"(?i)\b(?:has been|have been|was|were|is now|are now)\s+(?:successfully\s+)?(?:marked|frozen|unfrozen|resolved|closed|reopened|"
    r"assigned|updated|disabled|enabled|changed|applied|verified|sent|replied)\b"
    r"|\b(?:we|I)(?: have|'ve)\s+(?:already\s+)?(?:frozen|froze|unfrozen|resolved|closed|reopened|updated|disabled|enabled|changed|sent|replied|marked|assigned|verified)\b"
    r"|\bmarked (?:it |the ticket )?as\b|\bI(?: have|'ve| will now| now)?\s+(?:marked|frozen|froze|resolved|closed|updated|disabled|sent)\b"
    r"|\b(?:taken|took) (?:the )?(?:necessary )?steps\b|\bby (?:freezing|disabling|closing)\b")
STAFF_NOT_DONE = ('Nothing has been changed or sent. I can only prepare proposals that you approve in the app. '
                  'Start with the action and the exact ticket or account you want to change.')


QUARANTINED = ('This ticket contains instructions aimed at the assistant, so it was quarantined and Nova did not draft a reply. '
               'Please read it yourself and answer it manually. Nothing has been changed or sent.')


def filtered_answer(conn, db, run, answer):
    from .security_events import output
    from .agent.agent_access import vault_for
    # Check the actual text that will leave the bank, including restored aliases.
    from .documents.output import restore
    filtered = _filtered_answer(conn, db, run, restore(conn, db, run, answer, vault_for(db, run)))
    output(conn, run, answer, filtered)
    return filtered


def _filtered_answer(conn, db, run, answer):
    from .agent.disclosure import wants_balance
    verified_balance = False
    intent = json.loads(decrypt_secret(db, run['bound_request_json']))
    document_turn = intent['tool'] == 'ask_document'
    staff = conn.execute("SELECT role FROM users WHERE id=?", (run['owner_id'],)).fetchone()
    customer = staff and staff[0] == 'customer'
    if staff and staff[0] != 'customer' and conn.execute(
            "SELECT 1 FROM agent_calls WHERE run_id=? AND name='read_ticket' AND reason IN ('SOURCE_INJECTION','SOURCE_GUARD_UNAVAILABLE')",
            (run['id'],)).fetchone():
        return QUARANTINED
    if not document_turn and staff and staff[0] != 'customer' and STAFF_FALSE_DONE.search(answer) and not conn.execute(
            'SELECT 1 FROM tool_approvals WHERE run_id=? LIMIT 1', (run['id'],)).fetchone():
        return STAFF_NOT_DONE
    unsafe_link = re.search(r'(?:https?://|NB_CANARY_|eyJ[A-Za-z0-9_-]{20,}\.)', answer)
    if unsafe_link:
        answer = 'I could not safely display that response. Please use the banking screens or contact support.'
    proposal = conn.execute('SELECT name FROM tool_approvals WHERE run_id=? LIMIT 1', (run['id'],)).fetchone()
    if proposal and proposal[0].startswith('propose_'):
        count = conn.execute('SELECT COUNT(*) FROM tool_approvals WHERE run_id=?', (run['id'],)).fetchone()[0]
        answer = (f'I prepared {count} proposal{"s" if count > 1 else ""} below. Nothing has been sent or changed yet. '
                  'Read each one and approve or decline it; approved actions are recorded under your name.')
    elif proposal:
        answer = ('I prepared a proposal for your review below. No payment or card change has been made by the assistant. '
                  'Review it in the app. Enter any verification code only in the bank confirmation screen, never in this chat.')
    elif intent['tool'] in ('create_transfer', 'create_support_ticket'):
        answer = 'No action has been prepared or completed. Please use the banking screens or provide a specific request with the required details.'
    elif re.search(r'(?i)\b(?:send|provide|give|enter)\b.{0,40}\b(?:otp|pin|password|verification code)\b', answer):
        answer = 'Never share passwords, PINs or verification codes in chat. Use only the bank confirmation screen for codes.'
    elif document_turn:
        if FIRST_PERSON_DONE.search(answer):
            return NOT_DONE  # A bank-authored warning must not be attributed to the file.
    elif not customer and (FALSE_DONE.search(answer) or (intent['tool'] not in STATUS_READS and claims_status(answer))):
        answer = NOT_DONE
    elif intent['tool'] in ('get_cards', 'get_savings'):
        answer, verified_balance = product_financial_answer(conn, run, intent)
    elif intent['tool'] == 'get_account_balance' and wants_balance(intent):
        # Render financial facts at the bank boundary, for previews and final text alike.
        # Model prose and historical answers are never a source of current balances.
        call = conn.execute("SELECT result_json FROM agent_calls WHERE run_id=? AND name='get_account_balance' AND decision='ALLOW' ORDER BY ordinal DESC LIMIT 1", (run['id'],)).fetchone()
        if call:
            result = json.loads(call[0])
            label = 'Total payment account balance' if result.get('scope') == 'all_payment_accounts' else f'Account {result.get("id", "")} balance'
            answer = f'{label}: **{result["balance_vnd"]:,} VND**.'
            from .agent.agent_access import vault_for
            answer = vault_for(db, run).restore(answer)
            verified_balance = True
        else:
            answer = 'I have not verified your current balance. Please check the dashboard or ask me to check again.'
    else:
        claim = customer and (FALSE_DONE.search(answer) or claims_status(answer) or opens_topic(intent.get('text', ''), answer))
        facts = []
        if customer and not unsafe_link and (claim or intent['tool'] in STATUS_READS):
            asked = intent['tool'] in STATUS_READS or USER_TOPIC.search(intent.get('text', ''))
            facts = status_facts(conn, run, single_lookup_only=not asked)
        if facts:
            answer = render_status(facts)
        elif claim:
            answer = NOT_DONE
        else:
            answer = cite_retrieved_sources(conn, run, answer)
    from .agent.disclosure import filter_answer
    answer = filter_answer(conn, run['owner_id'], intent, answer, verified_balance=verified_balance, run_id=run['id'])
    if intent.get('tool') == 'ask_document':
        from .documents.output import attribute
        answer = attribute(conn, db, run, answer)
    return answer


def product_financial_answer(conn, run, intent):
    """Render only requested product totals from a successful bank tool read."""
    from .agent.disclosure import financial_classes
    requested = financial_classes(intent)
    call = conn.execute("SELECT result_json FROM agent_calls WHERE run_id=? AND name=? AND decision='ALLOW' ORDER BY ordinal DESC LIMIT 1",
        (run['id'], intent['tool'])).fetchone()
    if not call:
        return 'I have not verified those current amounts. Please check the banking screen or ask me to check again.', False
    items = json.loads(call[0]).get('items', [])
    if intent['tool'] == 'get_cards':
        items = [item for item in items if item.get('kind') == 'CREDIT']
        fields = [('card_debt', 'outstanding_vnd', 'Credit card debt'),
            ('card_available', 'available_credit_vnd', 'Available credit on your cards'),
            ('card_limit', 'credit_limit_vnd', 'Credit card limit')]
    else:
        fields = [('savings_balance', 'principal_vnd', 'Active savings principal'),
            ('savings_interest', 'projected_interest_vnd', 'Projected interest on active savings'),
            ('savings_interest', 'interest_paid_vnd', 'Paid savings interest')]
    lines = []
    for category, field, label in fields:
        if category not in requested:
            continue
        rows = [item for item in items if intent['tool'] != 'get_savings' or field == 'interest_paid_vnd' or item.get('status') == 'ACTIVE']
        total = sum(item.get(field, 0) for item in rows if type(item.get(field, 0)) is int)
        lines.append(f'{label}: **{total:,} VND**.')
    return '\n'.join(lines) or 'No financial amounts were requested.', True


def cite_retrieved_sources(conn, run, answer):
    sources = []
    calls = conn.execute("SELECT result_json FROM agent_calls WHERE run_id=? AND name='search_knowledge' AND decision='ALLOW' ORDER BY ordinal", (run['id'],)).fetchall()
    for call in calls:
        for source in json.loads(call[0]).get('sources', []):
            key = source.get('document_id', '')
            approved = conn.execute("SELECT 1 FROM knowledge_documents WHERE id=? AND status='PUBLISHED' AND trust_level='approved'", (key,)).fetchone()
            if approved and key not in sources:
                sources.append(key)
    cited = set(re.findall(r'\bKB-[A-Za-z0-9_-]+', answer))
    if cited - set(sources):
        answer = 'I could not verify the cited source. Please check the approved sources below or ask again.'
    if calls and not sources:
        return 'No approved source is available for this answer. Please search again or contact support.'
    missing = [key for key in sources if '[' + key + ']' not in answer]
    if missing:
        answer += '\n\nSources: ' + ', '.join('[' + key + ']' for key in missing)
    return answer
