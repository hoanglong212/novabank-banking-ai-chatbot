from tests.acceptance_helpers import *


def test_qr_origin_survives_draft_reload_and_decode_logs_no_payload(client):
    who = login(client)
    draft = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'Lunch', 'source_origin': 'qr'})
    assert draft.status_code == 201, draft.text
    assert client.get('/api/transfers/' + draft.json()['id'], headers=who).json()['source_origin'] == 'qr'
    bad = client.post('/api/qr/decode', headers=who, json={'payload': 'https://attacker.invalid/private'})
    assert bad.status_code == 422
    with get_db().connect() as conn:
        row = conn.execute("SELECT decision,detail_json FROM security_events WHERE event='qr_scanned'").fetchone()
        assert row['decision'] == 'DENY' and 'attacker' not in row['detail_json']
    normal = client.post('/api/transfers', headers=who, json={'to_account': 'ACC-BOB-001', 'amount_vnd': 10000, 'content': 'Normal'})
    assert normal.status_code == 201 and normal.json()['source_origin'] == 'manual'
