"""Bank-owned filtering shared by live previews and persisted final answers."""
import json
import re
from .auth_crypto import decrypt_secret

# The assistant never executes money movement or account changes itself, so a claim that it did is false.
# Plain status reads ("TX-1003 has been completed") are left alone.
FALSE_DONE = re.compile(
    r"(?i)\b(?:(?:has|have) been (?:successfully )?(?:processed|sent|paid|transferred|submitted|created|executed|made)"
    r"|processed successfully|(?:is|was) now (?:complete|completed|successful|paid|sent)"
    r"|I(?: have|'ve)? (?:successfully |just )?(?:sent|paid|transferred|processed|created|submitted|executed|completed)\b)")
NOT_DONE = ('Nothing has been sent, paid or changed. I cannot complete payments, transfers or tickets from chat. '
            'Put the whole request in one message with the amount and recipient, and I will prepare '
            'a draft for you to review and confirm with an OTP. You can also use the Transfer screen.')


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
    filtered = _filtered_answer(conn, db, run, vault_for(db, run).restore(answer))
    output(conn, run, answer, filtered)
    return filtered


def _filtered_answer(conn, db, run, answer):
    from .agent.disclosure import wants_balance
    verified_balance = False
    staff = conn.execute("SELECT role FROM users WHERE id=?", (run['owner_id'],)).fetchone()
    if staff and staff[0] != 'customer' and conn.execute(
            "SELECT 1 FROM agent_calls WHERE run_id=? AND name='read_ticket' AND reason IN ('SOURCE_INJECTION','SOURCE_GUARD_UNAVAILABLE')",
            (run['id'],)).fetchone():
        return QUARANTINED
    if staff and staff[0] != 'customer' and STAFF_FALSE_DONE.search(answer) and not conn.execute(
            'SELECT 1 FROM tool_approvals WHERE run_id=? LIMIT 1', (run['id'],)).fetchone():
        return STAFF_NOT_DONE
    if re.search(r'(?:https?://|NB_CANARY_|eyJ[A-Za-z0-9_-]{20,}\.)', answer):
        answer = 'I could not safely display that response. Please use the banking screens or contact support.'
    proposal = conn.execute('SELECT name FROM tool_approvals WHERE run_id=? LIMIT 1', (run['id'],)).fetchone()
    intent = json.loads(decrypt_secret(db, run['bound_request_json']))
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
    elif FALSE_DONE.search(answer):
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
    elif not proposal:
        answer = cite_retrieved_sources(conn, run, answer)
    from .agent.disclosure import filter_answer
    answer = filter_answer(conn, run['owner_id'], intent, answer, verified_balance=verified_balance, run_id=run['id'])
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
