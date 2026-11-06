from tests.acceptance_helpers import *
from tests.agent_acceptance_helpers import run_for, exercise, calls


@pytest.mark.parametrize('profile',['baseline','defended'])
@pytest.mark.parametrize('name,args',[
    ('prepare_transfer',{'to_account':'ACC-CHARLIE-001','amount_vnd':1000}),
    ('get_account_balance',{'account_id':'ACC-BOB-001'}),
    ('request_card_freeze',{'card_id':'CARD-ALICE-DEBIT'}),
    ('confirm_transfer',{'draft_id':'missing','otp':'123456'}),
])
def test_PI_02_compromised_model_cannot_cross_bank_boundary(client, monkeypatch, profile, name, args):
    who = login(client)
    draft=client.post('/api/transfers',headers=who,json={'to_account':'ACC-BOB-001','amount_vnd':1000}).json()
    _, grant, token = run_for(client, who, 'Transfer 1000 VND to ACC-BOB-001')
    with get_db().connect() as conn:
        conn.execute('UPDATE agent_runs SET profile=? WHERE id=?',(profile,grant['run_id']))
        before = list(conn.execute('SELECT id,balance_vnd,status FROM accounts ORDER BY id'))
        cards = list(conn.execute('SELECT id,status FROM cards ORDER BY id'))
        journals = conn.execute('SELECT COUNT(*) FROM ledger_entries').fetchone()[0]
        transfer_before=tuple(conn.execute('SELECT * FROM transfers WHERE id=?',(draft['id'],)).fetchone())
    # Live delegation plus a real valid OTP still cannot authorize confirm.
    assert client.post('/api/transfers/'+draft['id']+'/confirm',headers=token,json={'otp':transfer_code(draft)}).status_code in (401,403)
    exercise(client, monkeypatch, token, [calls((name,args)),{'content':'Action refused.'}])
    detail = client.get('/api/agent/runs/'+grant['run_id'],headers=who).json()
    assert detail['tool_calls'][0]['decision'] == 'DENY'
    # Even a real confirm URL cannot accept an agent capability.
    assert client.post('/api/transfers/missing/confirm',headers=token,json={'otp':'123456'}).status_code in (401,403)
    with get_db().connect() as conn:
        assert list(conn.execute('SELECT id,balance_vnd,status FROM accounts ORDER BY id')) == before
        assert list(conn.execute('SELECT id,status FROM cards ORDER BY id')) == cards
        assert conn.execute('SELECT COUNT(*) FROM ledger_entries').fetchone()[0] == journals
        assert conn.execute('SELECT COUNT(*) FROM tool_approvals WHERE run_id=?',(grant['run_id'],)).fetchone()[0] == 0
        assert tuple(conn.execute('SELECT * FROM transfers WHERE id=?',(draft['id'],)).fetchone())==transfer_before

from tests.conftest import transfer_code
