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
            'Put the whole request in one message, for example "transfer 50,000 VND to ACC-BOB-001", and I will prepare '
            'a draft for you to review and confirm with an OTP. You can also use the Transfer screen.')


# Staff runs: the bank applies changes only after approval, so "marked as resolved" / "froze the account" is false.
STAFF_FALSE_DONE = re.compile(
    r"(?i)\b(?:has been|have been|was|were|is now|are now)\s+(?:successfully\s+)?(?:marked|frozen|unfrozen|resolved|closed|reopened|"
    r"assigned|updated|disabled|enabled|changed|applied|verified|sent|replied)\b"
    r"|\b(?:we|I)(?: have|'ve)\s+(?:already\s+)?(?:frozen|froze|unfrozen|resolved|closed|reopened|updated|disabled|enabled|changed|sent|replied|marked|assigned|verified)\b"
    r"|\bmarked (?:it |the ticket )?as\b|\bI(?: have|'ve| will now| now)?\s+(?:marked|frozen|froze|resolved|closed|updated|disabled|sent)\b"
    r"|\b(?:taken|took) (?:the )?(?:necessary )?steps\b|\bby (?:freezing|disabling|closing)\b")
STAFF_NOT_DONE = ('Nothing has been changed or sent. I can only prepare proposals that you approve in the app. '
                  'Start with the action, for example "Reply to TKT-123 and mark it resolved" or "Freeze account ACC-BOB-001".')


QUARANTINED = ('This ticket contains instructions aimed at the assistant, so it was quarantined and Nova did not draft a reply. '
               'Please read it yourself and answer it manually. Nothing has been changed or sent.')


def filtered_answer(conn, db, run, answer):
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
    elif not proposal:
        answer = cite_retrieved_sources(conn, run, answer)
    return answer


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
