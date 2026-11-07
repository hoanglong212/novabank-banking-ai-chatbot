from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


@pytest.mark.parametrize('answer', [
    'The transaction to BOB-ACC-001 for 54,000 VND has been processed successfully. The payment is now completed.',
    'I have created a support ticket (TKT-7F11311181F6) for your pending transaction.',
    'Done! I transferred 54,000 VND to Bob.',
])
def test_assistant_cannot_claim_an_action_it_did_not_take(client, answer):
    who = login(client); cid, _, token = run_for(client, who, 'ok')
    text = client.post('/api/agent/finish', headers=token, json={'answer': answer, 'latency_ms': 10}).json()['message']['content']
    assert text.startswith('Nothing has been sent') and '54,000' not in text


def test_status_reads_are_not_rewritten(client):
    who = login(client); _, _, token = run_for(client, who, 'Check transaction TX-1003')
    answer = 'Transaction TX-1003 of 45,000 VND has been completed.'
    assert client.post('/api/agent/finish', headers=token, json={'answer': answer, 'latency_ms': 10}).json()['message']['content'] == answer
