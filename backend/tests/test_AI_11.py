from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for


@pytest.mark.parametrize('answer', ['The six-month annual rate is 5%.', 'The rate is 5% [KB-invented].'])
def test_AI_11_answer_cites_only_retrieved_approved_sources(client, answer):
    who = login(client); cid, run, token = run_for(client, who, 'What is the savings interest rate?')
    result = client.post('/api/agent/tools', headers=token, json={'name':'search_knowledge','arguments':{'query':'savings interest six months'}}).json()
    assert result['decision'] == 'ALLOW'
    assert 'KB-savings' in [r['document_id'] for r in result['result']['sources']]
    response = client.post('/api/agent/finish', headers=token, json={'answer':answer,'latency_ms':10})
    assert response.status_code == 200
    text = response.json()['message']['content']
    assert '[KB-savings]' in text and 'KB-invented' not in text
    assert client.get('/api/conversations/'+cid+'/messages', headers=who).json()[-1]['content'] == text


def test_AI_11_no_citation_for_revoked_or_unretrieved_document(client):
    who = login(client); _, run, token = run_for(client, who, 'What is the savings interest rate?')
    client.post('/api/agent/tools', headers=token, json={'name':'search_knowledge','arguments':{'query':'savings interest six months'}})
    with get_db().connect() as conn:
        conn.execute("UPDATE knowledge_documents SET status='DRAFT' WHERE id='KB-savings'")
    response = client.post('/api/agent/finish', headers=token, json={'answer':'The rate is 5% [KB-savings].','latency_ms':10})
    assert '[KB-savings]' not in response.json()['message']['content']
