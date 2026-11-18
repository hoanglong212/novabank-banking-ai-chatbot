"""Every third-party-writable free-text field a read tool returns must be listed in provenance.FIELD_TRUST.

Each such column on the seed gets a unique marker. Every read tool in the registry is called, and the raw
bank result (before the quarantine filter, i.e. what FIELD_TRUST is meant to cover) is walked. A marker found
under a key that FIELD_TRUST does not list for that tool is an untracked untrusted field. Test only: no app
behaviour changes here.
"""
from tests.acceptance_helpers import client, get_db, login  # noqa: F401
from tests.test_week7 import grant_for
from tests.test_documents_api import engines, upload  # noqa: F401

STAMP = '2026-10-30T09:00:00+00:00'
# (table, column) -> marker; every value is text a party other than bank logic can write.
MARKERS = {
    ('transactions', 'description'): 'ftmemo1', ('product_transaction_details', 'counterparty_name'): 'ftcounterparty2',
    ('beneficiaries', 'holder_name'): 'ftholder3', ('beneficiaries', 'nickname'): 'ftnickname4',
    ('account_labels', 'nickname'): 'ftlabel5', ('card_transactions', 'merchant'): 'ftmerchant6',
    ('savings', 'label'): 'ftsavings7', ('bills', 'provider'): 'ftprovider8', ('bills', 'customer_code'): 'ftcode9',
    ('support_tickets', 'subject'): 'ftsubject10', ('support_tickets', 'description'): 'ftticket11',
    ('ticket_messages', 'body'): 'ftreply12', ('knowledge_documents', 'title'): 'fttitle13',
    ('knowledge_documents', 'content'): 'ftcontent14', ('knowledge_documents', 'source'): 'ftsource15',
    ('banking_audit', 'reason_code'): 'ftaudit16',
}
STAFF_READS = {'list_tickets', 'read_ticket', 'get_customer_summary', 'list_failed_transfers', 'get_user_count',
               'list_transactions', 'get_bank_overview', 'list_customers', 'list_accounts', 'get_bank_settings',
               'list_audit_events'}
ARGUMENTS = {'get_transaction_status': {'transaction_id': 'TX-FT'}, 'get_recent_transactions': {'limit': 20},
             'get_spending_summary': {'month': '2026-10'}, 'read_ticket': {'ticket_id': 'TKT-FT'},
             'get_customer_summary': {'user_id': 'alice'}, 'list_transactions': {'limit': 50},
             'list_audit_events': {'limit': 50}, 'list_tickets': {'limit': 50},
             'search_knowledge': {'query': 'transfer fee policy ftcontent14'}}
# Some tools require the user message to carry the matching read intent or name the target.
PROMPTS = {'get_account_balance': 'What is my balance?', 'read_ticket': 'Read ticket TKT-FT'}


def text(column):
    return MARKERS[column] + ' third-party text'


def plant(conn):
    conn.execute("INSERT INTO transactions VALUES ('TX-FT','ACC-ALICE-001',10000,'in','COMPLETED',?,'2026-10-30',?)",
                 (text(('transactions', 'description')), STAMP))
    conn.execute("INSERT INTO product_transaction_details VALUES ('TX-FT','FT-JOURNAL','FIXTURE','FT-SOURCE',10000,?,0)",
                 (text(('product_transaction_details', 'counterparty_name')),))
    conn.execute("INSERT INTO beneficiaries VALUES ('FT-BEN','alice','ACC-BOB-001','NovaBank',?,?,'untrusted',?)",
                 (text(('beneficiaries', 'holder_name')), text(('beneficiaries', 'nickname')), STAMP))
    conn.execute("INSERT INTO account_labels VALUES ('ACC-ALICE-001',?) ON CONFLICT(account_id) DO UPDATE SET nickname=excluded.nickname",
                 (text(('account_labels', 'nickname')),))
    conn.execute("INSERT INTO cards VALUES ('CARD-FT','alice','ACC-ALICE-001','DEBIT','4242','ACTIVE',0,0,?)", (STAMP,))
    conn.execute("INSERT INTO card_transactions VALUES ('FT-CARD-TX','CARD-FT',10000,'CARD_PURCHASE',?,'FT-JOURNAL-2',?)",
                 (text(('card_transactions', 'merchant')), STAMP))
    conn.execute("INSERT INTO savings VALUES ('FT-SAV','alice','ACC-ALICE-001',?,100000,3,450,?,'2027-01-30','ACTIVE',NULL,0)",
                 (text(('savings', 'label')), STAMP))
    conn.execute("INSERT INTO bills VALUES ('FT-BILL','alice',?,'ELECTRICITY',?,10000,'2026-11-20','UNPAID',1,NULL,NULL)",
                 (text(('bills', 'provider')), text(('bills', 'customer_code'))))
    conn.execute("INSERT INTO support_tickets VALUES ('TKT-FT','alice',?,?,'OPEN',?)",
                 (text(('support_tickets', 'subject')), text(('support_tickets', 'description')), STAMP))
    conn.execute("INSERT INTO ticket_messages VALUES ('FT-MSG','TKT-FT','alice',?,?)", (text(('ticket_messages', 'body')), STAMP))
    conn.execute("INSERT INTO knowledge_documents VALUES ('KB-FT',?,?,?,'approved','PUBLISHED',NULL,NULL,?,?)",
                 (text(('knowledge_documents', 'title')), 'Transfer fee policy. ' + text(('knowledge_documents', 'content')),
                  text(('knowledge_documents', 'source')), STAMP, STAMP))
    conn.execute("INSERT INTO banking_audit VALUES ('FT-AUDIT','alice','SYNTHETIC_FIXTURE','FT-SOURCE',?,NULL,NULL,?)",
                 (text(('banking_audit', 'reason_code')), STAMP))


def marked_fields(value, found, key=None):
    if isinstance(value, list):
        for item in value:
            marked_fields(item, found, key)
    elif isinstance(value, dict):
        for name, item in value.items():
            marked_fields(item, found, name)
    elif isinstance(value, str) and key is not None:
        for column, marker in MARKERS.items():
            if marker in value:
                found.add((key, column))


def test_every_third_party_text_field_in_read_results_is_in_field_trust(client, monkeypatch, engines):
    from app.agent import agent_access, provenance
    with get_db().connect() as conn:
        plant(conn)
    raw, pending = {}, {}
    real_filtered, real_observe = agent_access.quarantine.filtered, agent_access.provenance.observe

    def filtered(conn, name, result):
        pending[name] = result
        return real_filtered(conn, name, result)

    def observe(conn, run, name, result):
        raw.setdefault(name, []).append(pending.pop(name, result))
        return real_observe(conn, run, name, result)

    monkeypatch.setattr(agent_access.quarantine, 'filtered', filtered)
    monkeypatch.setattr(agent_access.provenance, 'observe', observe)
    reads = sorted(name for name in agent_access.MODELS if not name.startswith(('prepare_', 'propose_', 'request_')))
    sessions = {'alice': login(client, 'alice'), 'admin': login(client, 'admin')}
    doc = upload(client, sessions['alice'], b'ftdoccontent third party text', 'ftdocname.txt').json()['id']
    MARKERS[('doc_chunks', 'text')] = 'ftdoccontent'
    MARKERS[('documents', 'filename_display')] = 'ftdocname'
    arguments = {**ARGUMENTS, 'ask_document': {'document_id': doc, 'question': 'Summarize'}}
    prompts = {**PROMPTS, 'ask_document': 'Summarize document ' + doc}
    decisions = {}
    for name in reads:
        who = sessions['admin' if name in STAFF_READS else 'alice']
        _, _, token = grant_for(client, who, prompts.get(name, 'Show me ' + name), 'baseline')
        response = client.post('/api/agent/tools', headers=token, json={'name': name, 'arguments': arguments.get(name, {})})
        decisions[name] = (response.status_code, response.json().get('decision'), response.json().get('reason'))
    assert {name: d for name, d in decisions.items() if d[:2] != (200, 'ALLOW')} == {}, 'every read tool must be exercised'
    assert set(raw) == set(reads)

    surfaced, missing = set(), []
    for name in reads:
        found = set()
        for result in raw[name]:
            marked_fields(result, found)
        for key, column in sorted(found):
            surfaced.add(column)
            if key not in provenance.FIELD_TRUST.get(name, ()):
                missing.append(f'{name}.{key} <- {column[0]}.{column[1]}')
    # The fixture must actually reach the tools; otherwise the check below would pass vacuously.
    assert surfaced == set(MARKERS), sorted(set(MARKERS) - surfaced)
    assert missing == [], 'untrusted free-text fields missing from FIELD_TRUST:\n' + '\n'.join(missing)
