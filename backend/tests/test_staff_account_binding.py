"""Account-action targets stay bound even when the staff text mentions a ticket."""
import pytest

from tests.acceptance_helpers import client, get_db, login
from tests.test_week7 import grant_for


@pytest.mark.parametrize('text,status', [
    ('Freeze ACC-CHARLIE-001 for TKT-DEMO. ACC-BOB-001 is fine.', 'FROZEN'),
    ('For TKT-DEMO, please freeze account ACC-CHARLIE-001. ACC-BOB-001 is fine.', 'FROZEN'),
    ('ACC-BOB-001 is fine. Freeze ACC-CHARLIE-001 for TKT-DEMO.', 'FROZEN'),
    ('Unfreeze account ACC-CHARLIE-001 for TKT-DEMO. ACC-BOB-001 is fine.', 'ACTIVE'),
    ('Khóa tài khoản ACC-CHARLIE-001 cho TKT-DEMO. ACC-BOB-001 vẫn bình thường.', 'FROZEN'),
])
def test_ticket_reference_cannot_redirect_account_action_and_explicit_target_still_works(client, text, status):
    admin = login(client, 'admin')
    with get_db().connect() as conn:
        before = list(conn.execute('SELECT id,status FROM accounts ORDER BY id'))
    _, denied_run, token = grant_for(client, admin, text)
    response = client.post('/api/agent/tools', headers=token, json={
        'name': 'propose_account_status', 'arguments': {'account_id': 'ACC-BOB-001', 'status': status}})
    assert response.status_code == 200
    assert (response.json()['decision'], response.json()['reason']) == ('DENY', 'USER_INTENT_MISMATCH')
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM tool_approvals WHERE run_id=?', (denied_run['run_id'],)).fetchone()[0] == 0
    # Fresh authenticated staff input explicitly names Charlie. No tool result
    # or model text supplies this target, and creation still requires approval.
    _, _, token = grant_for(client, admin, text)
    allowed = client.post('/api/agent/tools', headers=token, json={
        'name': 'propose_account_status', 'arguments': {'account_id': 'ACC-CHARLIE-001', 'status': status}}).json()
    assert allowed['decision'] == 'ALLOW'
    assert allowed['result']['status'] == 'PENDING'
    with get_db().connect() as conn:
        assert list(conn.execute('SELECT id,status FROM accounts ORDER BY id')) == before
