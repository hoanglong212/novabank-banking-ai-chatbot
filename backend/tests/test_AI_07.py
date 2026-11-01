from tests.acceptance_helpers import *
from tests.agent_acceptance_helpers import run_for, exercise, calls


def test_AI_07_actual_model_and_classifier_requests_hide_known_identity_and_secrets(client, monkeypatch):
    who = login(client)
    profile = client.get('/api/customer/profile', headers=who).json()
    beneficiary(client, who, nickname='BOB TRAN rent')
    cid, grant, token = run_for(client, who, 'Show my accounts and recipients for '+profile['name']+' ACC-ALICE-001')
    # Historical/user-authored sources are untrusted, including previously stored secrets.
    get_db().append_message(cid, 'user', 'Old note: '+profile['name']+' account ACC-ALICE-001 OTP: 739284')
    with get_db().connect() as conn:
        conn.execute("UPDATE agent_runs SET profile='defended' WHERE id=?", (grant['run_id'],))
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    payloads, _, events = exercise(client, monkeypatch, token, [
        calls(('get_accounts',{}), ('get_beneficiaries',{})), {'content':'Your accounts are available.'}])
    assert any(p.get('format') for p in payloads), 'Must capture the classifier request as well'
    wire = json.dumps(payloads)
    for raw in (profile['name'], 'ALICE NGUYEN', 'BOB TRAN', 'ACC-ALICE-001', 'ACC-BOB-001', '739284', profile['email']):
        assert raw.casefold() not in wire.casefold(), 'Raw identity/secret reached the model: '+raw
    assert '<ACCOUNT_' in wire and '<NAME_' in wire
    assert any(e.startswith('event: complete') for e in events)


def test_AI_07_pseudonymous_account_can_be_restored_at_authorized_boundary(client):
    who = login(client); _, _, token = run_for(client, who)
    accounts = client.post('/api/agent/tools', headers=token, json={'name':'get_accounts','arguments':{}}).json()
    account = accounts['result']['items'][0]['id']
    assert account.startswith('<ACCOUNT_')
    balance = client.post('/api/agent/tools', headers=token, json={'name':'get_account_balance','arguments':{'account_id':account}}).json()
    assert balance['decision'] == 'ALLOW' and balance['result']['balance_vnd'] == 12500000


def test_AI_07_transfer_tool_schema_and_bound_hint_do_not_reintroduce_account_ids(client,monkeypatch):
    who=login(client)
    _,_,token=run_for(client,who,'Transfer 1000 VND to ACC-BOB-001')
    payloads,_,_=exercise(client,monkeypatch,token,[{'content':'Please review the transfer.'}])
    assert 'ACC-BOB-001' not in json.dumps(payloads)
