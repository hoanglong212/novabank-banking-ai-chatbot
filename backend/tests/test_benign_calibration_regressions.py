from tests.acceptance_helpers import login, get_db
from tests.test_AI_12 import run_for
from tests.test_customer_products import confirm


def test_bill_read_accepts_declared_status_filter_and_rejects_extra_authority(client):
    who = login(client)
    bills = client.get('/api/products/bills', headers=who).json()['items']
    action = client.post('/api/products/actions', headers=who, json={
        'kind': 'PAY_BILL', 'resource_id': bills[0]['id'], 'account_id': 'ACC-ALICE-001'}).json()
    assert confirm(client, who, action, 'bill-filter-control').status_code == 200
    bills = client.get('/api/products/bills', headers=who).json()['items']
    expected = {(item['status'], item['amount_vnd'], item['due_date']) for item in bills if item['status'] == 'UNPAID'}
    assert expected and any(item['status'] == 'PAID' for item in bills)
    _, _, token = run_for(client, who, 'Show my unpaid bills.')
    invalid = client.post('/api/agent/tools', headers=token, json={'name': 'get_bills', 'arguments': {'owner_id': 'bob'}}).json()
    assert invalid['decision'] == 'DENY' and invalid['reason'] == 'INVALID_ARGUMENTS'
    result = client.post('/api/agent/tools', headers=token, json={'name': 'get_bills', 'arguments': {'status': 'unpaid'}}).json()
    assert result['decision'] == 'ALLOW', result
    assert {(item['status'], item['amount_vnd'], item['due_date']) for item in result['result']['items']} == expected
    all_bills = client.post('/api/agent/tools', headers=token, json={'name': 'get_bills', 'arguments': {}}).json()
    assert len(all_bills['result']['items']) == len(bills)


def test_detector_outage_revokes_run_without_quarantining_or_learning_an_attack(client, monkeypatch):
    from app.agent import source_screen
    who = login(client)
    async def unavailable(_):
        return {'injection': True, 'available': False, 'method': 'unavailable'}
    monkeypatch.setattr(source_screen, 'classify', unavailable)
    scores = []
    for _ in range(2):
        _, grant, token = run_for(client, who, 'Check transaction TX-1003')
        blocked = client.post('/api/agent/tools', headers=token, json={'name': 'get_transaction_status', 'arguments': {'transaction_id': 'TX-1003'}}).json()
        assert blocked['decision'] == 'DENY' and blocked['halt'] is True
        assert client.get('/api/agent/context', headers=token).status_code == 401
        with get_db().connect() as conn:
            assert not conn.execute("SELECT 1 FROM quarantined_sources WHERE source_id='tx:TX-1003' AND released_at IS NULL").fetchone()
            case = conn.execute('SELECT decision,score FROM risk_cases WHERE run_id=?', (grant['run_id'],)).fetchone()
            assert case['decision'] == 'deny'
            scores.append(case['score'])
    assert scores[0] == scores[1]
    async def recovered(_):
        return {'injection': False, 'available': True, 'method': 'qwen'}
    monkeypatch.setattr(source_screen, 'classify', recovered)
    _, _, token = run_for(client, who, 'Check transaction TX-1003')
    allowed = client.post('/api/agent/tools', headers=token, json={'name': 'get_transaction_status', 'arguments': {'transaction_id': 'TX-1003'}}).json()
    assert allowed['decision'] == 'ALLOW' and not allowed['result'].get('quarantined')
