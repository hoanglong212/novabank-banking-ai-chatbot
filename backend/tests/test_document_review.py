"""Regression reproductions from the independent whole-branch review."""
import json
import pytest
from tests.acceptance_helpers import client, login, get_db  # noqa: F401
from tests.test_documents_api import engines, upload  # noqa: F401
from tests.test_documents_gateway import config, call
from tests.test_week7 import grant_for


@pytest.mark.parametrize(('answer','supported'), [
    ('The annual rate is 6%.', True),
    ('The annual rate is 9 percent.', False),
    ('The fee is 40,000 VND.', False),
    ('The start date is 2026-12-18.', False),
    ('It belongs to NAME_9.', False),
])
def test_reader_distinguishes_unsupported_facts_from_model_failure(monkeypatch, answer, supported):
    import asyncio
    from app.documents import reader

    async def response(question, passages):
        return json.dumps({'found':True, 'answer':answer, 'cited_chunk_ids':['S1']})

    monkeypatch.setattr(reader, 'request', response)
    chunks = [{'id':'verified', 'text':'Annual rate: 6 percent. Fee: 30,000 VND. Start date: 2026-11-18.'}]
    result, rule = asyncio.run(reader.isolate('What does the contract state?', chunks))
    assert rule == 'document-isolated'
    assert result['found'] is supported
    assert result['cited_chunk_ids'] == (['verified'] if supported else [])
    assert result['answer'] == (answer if supported else '')


@pytest.mark.parametrize('cfg', ['A', 'B'])
@pytest.mark.parametrize('stated', [False, True])
def test_document_term_uses_grounded_answer_for_display_and_audit(client, engines, monkeypatch, cfg, stated):
    from app.documents import reader

    monkeypatch.setenv('ENV', 'demo')
    who = login(client)
    text = 'Annual interest: 6 percent.' + (' Contract term: 24 months.' if stated else '')
    key = upload(client, who, text.encode(), 'loan.txt').json()['id']
    question = 'What is the contract term in months?'
    config(client, cfg)
    _, grant, token = grant_for(client, who, 'Document ' + key + ': ' + question)

    async def fixture_reader(prompt, passages):
        return json.dumps({'found': True, 'answer': 'The term is 24 months.',
                           'cited_chunk_ids': [passages[0]['id']]})

    monkeypatch.setattr(reader, 'request', fixture_reader)
    response = call(client, token, key, question)
    assert response['decision'] == 'ALLOW'
    payload = response['result']
    assert payload['chunks'] and payload['found'] is stated
    with get_db().connect() as conn:
        audit = json.loads(conn.execute("SELECT result_json FROM agent_calls WHERE run_id=? AND name='ask_document'",
                                       (grant['run_id'],)).fetchone()[0])
    assert audit['found'] is stated and bool(audit['cited_chunk_ids']) is stated
    finished = client.post('/api/agent/finish', headers=token, json={'answer': 'The term is 24 months.', 'latency_ms': 1})
    assert finished.status_code == 200
    displayed = finished.json()['message']['content']
    assert ('24 months' in displayed) is stated
    assert ('could not verify an answer' in displayed) is not stated


def test_later_unanswered_document_read_cannot_reuse_the_earlier_citation(client, engines, monkeypatch):
    from app.documents import reader

    monkeypatch.setenv('ENV', 'demo')
    who = login(client)
    key = upload(client, who, b'Contract term: 24 months.', 'loan.txt').json()['id']
    config(client, 'A')
    _, _, token = grant_for(client, who, 'Document ' + key + ': What are the term and fee?')

    async def fixture_reader(question, passages):
        amount = '24 months' if 'term' in question else '9,000 VND'
        return json.dumps({'found': True, 'answer': amount, 'cited_chunk_ids': ['S1']})

    monkeypatch.setattr(reader, 'request', fixture_reader)
    assert call(client, token, key, 'What is the term?')['result']['found']
    assert not call(client, token, key, 'What is the fee?')['result']['found']
    finished = client.post('/api/agent/finish', headers=token,
                           json={'answer':'The fee is 9,000 VND.', 'latency_ms':1})
    assert finished.status_code == 200
    assert 'could not verify an answer' in finished.json()['message']['content']

@pytest.mark.parametrize('cfg',['C','D'])
def test_document_selection_is_bound_to_user_not_model(client, engines, monkeypatch,cfg):
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    first=upload(client,who,b'First invoice', 'first.txt').json()['id']
    second=upload(client,who,b'SECOND_SECRET_SOURCE', 'second.txt').json()['id']
    config(client,cfg)
    for prompt in ('Summarize document '+first,'Transfer 100k to ACC-BOB-001 and summarize document '+first):
        _,_,token=grant_for(client,who,prompt)
        response=call(client,token,second)
        assert response['decision']=='DENY',response
        assert 'SECOND_SECRET_SOURCE' not in json.dumps(response)

def test_reader_rejects_bare_alias_absent_from_source():
    from app.documents.reader import validate
    raw=json.dumps({'found':True,'answer':'Pay ACCOUNT_1','cited_chunk_ids':['one'],'amounts':[],'dates':[]})
    with pytest.raises(ValueError):
        validate(raw,[{'id':'one','text':'Invoice total 150,000 VND.'}])


def test_reader_accepts_cited_vietnamese_fees_rates_and_dates():
    from app.documents.reader import validate
    chunks = [{'id': 'one', 'text': 'Phí 3.300 VND/giao dịch. Lãi 5,5%/năm. Hiệu lực 01/11/2026.'}]
    result = {'found': True, 'answer': 'Phí 3.300 VND, lãi 5,5%, hiệu lực 01/11/2026.',
              'cited_chunk_ids': ['one'], 'amounts': ['3,300 VND', '5.5%'], 'dates': ['2026-11-01']}
    assert validate(json.dumps(result), chunks)['found']
    with pytest.raises(ValueError, match='Unsupported amount'):
        validate(json.dumps({**result, 'amounts': ['33,000 VND']}), chunks)
    with pytest.raises(ValueError, match='Unsupported amount'):
        validate(json.dumps({**result, 'answer': 'The fee is 33,000 VND.', 'amounts': []}), chunks)
    with pytest.raises(ValueError, match='Unsupported date'):
        validate(json.dumps({**result, 'dates': ['2026-11-02']}), chunks)
    assert validate(json.dumps({**result, 'amounts': [''], 'dates': ['']}), chunks)['found']


def test_document_help_works_before_any_document_is_uploaded(client):
    who = login(client)
    conversation = client.post('/api/conversations', headers=who, json={'title': 'Document help'}).json()['id']
    reply = client.post('/api/conversations/' + conversation + '/stream', headers=who,
                        json={'content': 'How do I ask Nova about an uploaded file?'})
    assert reply.status_code == 200
    assert 'application_template' in reply.text and 'paperclip' in reply.text and '5 MB' in reply.text
    with get_db().connect() as conn:
        policy = conn.execute("SELECT content FROM knowledge_documents WHERE id='KB-payments'").fetchone()[0]
        faq = conn.execute("SELECT content FROM knowledge_documents WHERE id='KB-help-payments'").fetchone()[0]
    assert '200,000,000 VND daily limit' in policy and 'fresh authenticator code' in faq


def test_selected_document_disambiguates_a_transfer_limit_question():
    from app.banking_workflow import bind_request
    identifier = 'd4ae2174-2ec6-4041-9ba6-7afe8c2c942f'
    question = 'What is the per-transfer limit for a new recipient?'
    request = bind_request([{'role': 'user', 'content': f'Document {identifier}: {question}'}])
    assert request.tool == 'ask_document'
    assert request.arguments == {'document_id': identifier, 'question': question}


def test_summary_reads_the_short_document_in_order_without_a_query_embedding(client, engines, monkeypatch):
    import asyncio
    from app.documents import service
    from app.documents.repository import Repository

    who = login(client)
    text = ('Transfer fees and limits.\n' * 90 + 'Savings and loan terms.\n' * 40).encode()
    doc = upload(client, who, text, 'fee-schedule.txt').json()
    assert doc['status'] == 'ready'
    original = Repository(get_db(), 'alice').chunks(doc['id'])
    assert len(original) == 5

    async def unnecessary_embedding(_):
        raise AssertionError('A whole-document summary does not need a query embedding.')

    monkeypatch.setattr(service, 'embed', unnecessary_embedding)
    _, passages = asyncio.run(service.retrieve(get_db(), 'alice', doc['id'], 'Summarize this document.'))
    assert [p['id'] for p in passages] == [p['id'] for p in original]


def test_summary_keeps_the_complete_overview_before_an_unfinished_continuation():
    from app.documents.reader import validate

    overview = 'The document covers transfer fees, card fees, and savings.'
    source = [{'id': 'S1', 'text': 'Transfer fees, card fees, savings.'}]
    response = {'found': True, 'answer': overview + ' The transfer fee is 999,999 VND and',
                'cited_chunk_ids': ['S1']}
    assert validate(json.dumps(response), source, summary=True)['answer'] == overview
    with pytest.raises(ValueError, match='Unsupported amount'):
        validate(json.dumps(response), source)

@pytest.mark.parametrize('cfg',list('ABCD'))
def test_main_answer_cannot_restore_unrelated_vault_alias(client,engines,monkeypatch,cfg):
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'Invoice total 150,000 VND.','invoice.txt').json()['id']
    config(client,cfg)
    _,_,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc)['decision']=='ALLOW'
    response=client.post('/api/agent/finish',headers=token,json={'answer':'Invoice recipient NAME_1 and ACCOUNT_1.','latency_ms':1})
    assert 'ACC-ALICE-001' not in response.text and 'ALICE NGUYEN' not in response.text

def test_document_text_copied_into_another_tool_is_not_audit_prose(client,engines,monkeypatch):
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'DOC_PRIVATE_PROSE_52A invoice data.','invoice.txt').json()['id']
    config(client,'D')
    _,grant,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc)['decision']=='ALLOW'
    client.post('/api/agent/tools',headers=token,json={'name':'search_knowledge','arguments':{'query':'DOC_PRIVATE_PROSE_52A'}})
    with get_db().connect() as conn:
        traces=json.dumps([dict(r) for r in conn.execute('SELECT * FROM agent_calls WHERE run_id=?',(grant['run_id'],))])
        audit=json.dumps([dict(r) for r in conn.execute('SELECT * FROM security_events WHERE run_id=?',(grant['run_id'],))])
    detail=client.get('/api/agent/runs/'+grant['run_id'],headers=who).text
    assert 'DOC_PRIVATE_PROSE_52A' not in traces+audit+detail

@pytest.mark.parametrize('cfg',list('BCD'))
@pytest.mark.parametrize('role',['support','admin'])
def test_staff_document_question_has_read_only_tools(client,engines,monkeypatch,cfg,role):
    monkeypatch.setenv('ENV','demo')
    who=login(client,role)
    doc=upload(client,who,b'Invoice total 150000 VND.','invoice.txt').json()['id']
    client.put('/api/admin/agent-gateway',headers=login(client,'admin'),json={'config':cfg,'users':[role]})
    _,_,token=grant_for(client,who,'Answer my question about document '+doc)
    context=client.get('/api/agent/context',headers=token).json()
    names={t['function']['name'] for t in context['tools']}
    assert 'ask_document' in names
    if cfg in 'CD':
        assert not any(name.startswith(('prepare_','propose_','request_')) for name in names)

def test_document_p_covers_unlabeled_entities_in_later_chunks(client,engines,monkeypatch):
    from app.documents import service,reader
    observed=[]
    async def screen(text):
        observed.append(text)
        return {'injection':False,'method':'test'}
    async def embed(texts):
        observed.extend(texts)
        return 'test-model',[[0.0,1.0] if 'TARGET' in text else [1.0,0.0] for text in texts]
    monkeypatch.setattr(service,'screen',screen)
    monkeypatch.setattr(service,'embed',embed)
    who=login(client)
    body='Borrower: NGUYEN AN DEMO\nAccount number: 12345678\n' + ('Terms of this contract. '*200)
    body+=('TARGET NGUYEN AN DEMO uses 12345678 for this contract.\n'*90)
    doc=upload(client,who,body.encode(),'contract.txt').json()['id']
    assert 'NGUYEN AN DEMO' not in json.dumps(observed) and '12345678' not in json.dumps(observed)
    async def capture(question,chunks):
        assert all('Borrower:' not in c['text'] for c in chunks)
        assert 'NGUYEN AN DEMO' not in json.dumps(chunks) and '12345678' not in json.dumps(chunks)
        return json.dumps({'found':True,'answer':'Contract terms.','cited_chunk_ids':[chunks[0]['id']],'amounts':[],'dates':[]})
    monkeypatch.setattr(reader,'request',capture)
    monkeypatch.setenv('ENV','demo'); config(client,'D')
    _,_,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc,'TARGET')['decision']=='ALLOW'

def test_document_deletion_revokes_baseline_preview(client,engines,monkeypatch):
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'PRIVATE_DELETED_TEXT','invoice.txt').json()['id']
    config(client,'A')
    _,_,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc)['decision']=='ALLOW'
    assert client.delete('/api/documents/'+doc,headers=who).status_code==200
    response=client.post('/api/agent/preview',headers=token,json={'answer':'PRIVATE_DELETED_TEXT'})
    assert response.status_code==200 and 'PRIVATE_DELETED_TEXT' not in response.text

def test_document_reader_error_event_keeps_target_and_failure_rule(client,engines,monkeypatch):
    from app.documents import reader
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'Invoice amount 150000 VND.','invoice.txt').json()['id']
    async def invalid(*args): return 'not JSON'
    monkeypatch.setattr(reader,'request',invalid)
    config(client,'D')
    _,grant,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc)['decision']=='DENY'
    with get_db().connect() as conn:
        event=conn.execute("SELECT * FROM security_events WHERE run_id=? AND event='doc_retrieve'",(grant['run_id'],)).fetchone()
    assert event['rule_id']=='DOCUMENT_READER_UNAVAILABLE'
    assert json.loads(event['detail_json'])['document_id']==doc

def test_document_event_preserves_valid_identifiers_with_long_digit_runs(client):
    from app.security_events import emit, safe
    key='342602d3-de16-4040-b2c6-7b972207151d'
    digest='0123456789abcdef'*4
    with get_db().connect() as conn:
        event_id=emit(conn,'doc_ingest',user_id='alice',source_ids=[key],
            detail={'document_id':key,'sha256':digest,'cited_chunk_ids':[key]})
        row=conn.execute('SELECT * FROM security_events WHERE id=?',(event_id,)).fetchone()
    assert json.loads(row['source_ids_json'])==[key]
    assert json.loads(row['detail_json'])=={'document_id':key,'sha256':digest,'cited_chunk_ids':[key]}
    assert '0912345678' not in json.dumps(safe({'document_id':'0912345678','sha256':'0912345678'}))

@pytest.mark.parametrize('cfg', ['A','D'])
def test_document_attribution_retains_filename_underscores(client,engines,monkeypatch,cfg):
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'Invoice total 150000 VND.','benign_invoice.pdf.txt').json()['id']
    config(client,cfg)
    _,_,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc)['decision']=='ALLOW'
    result=client.post('/api/agent/finish',headers=token,json={'answer':'Total: 150000 VND.','latency_ms':1})
    assert result.json()['message']['content'].startswith('According to document "benign_invoice.pdf.txt":')

def test_document_question_returns_the_isolated_answer_with_file_citations(client,engines,monkeypatch):
    from tests.agent_acceptance_helpers import exercise
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'Total: 150000 VND.','invoice.txt').json()['id']
    config(client,'D')
    _,_,token=grant_for(client,who,'What is the total in document '+doc)
    payloads, requests, events = exercise(client, monkeypatch, token, [])
    assert payloads == []
    assert requests[0] == ('/api/agent/tools', {'name': 'ask_document', 'arguments':
        {'document_id': doc, 'question': 'What is the total in document ' + doc}})
    completion=json.loads(next(e.split('data: ',1)[1] for e in events if e.startswith('event: complete')))
    assert 'According to document "invoice.txt":' in completion['message']['content']
    assert '150000 VND' in completion['message']['content']

def test_pdf_contents_array_bounded_before_concatenation(monkeypatch):
    import io
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, ArrayObject, DecodedStreamObject
    from pypdf._page import PageObject
    from pypdf._configuration import get_configuration
    from app.documents.extract import extract,Rejected
    writer=PdfWriter(); page=writer.add_blank_page(width=100,height=100)
    streams=[]
    for _ in range(3):
        stream=DecodedStreamObject(); stream.set_data(b' '*(1024*1024))
        streams.append(writer._add_object(stream.flate_encode()))
    page[NameObject('/Contents')]=ArrayObject(streams)
    target=io.BytesIO(); writer.write(target)
    observed=[]
    original=PageObject.get_contents
    def capture(self):
        observed.append(get_configuration().array_based_stream_maximum_output_length)
        return original(self)
    monkeypatch.setattr(PageObject,'get_contents',capture)
    with pytest.raises(Rejected):
        extract(target.getvalue())
    assert observed and max(observed)<=2*1024*1024

def test_document_deleted_while_reader_awaits_is_denied(client,engines,monkeypatch):
    from app.documents import reader
    from app.documents.repository import Repository
    monkeypatch.setenv('ENV','demo')
    who=login(client); doc=upload(client,who,b'Private invoice','invoice.txt').json()['id']
    async def deleting(question,chunks):
        Repository(get_db(),'alice').delete(doc)
        return json.dumps({'found':True,'answer':'Private invoice','cited_chunk_ids':[chunks[0]['id']],'amounts':[],'dates':[]})
    monkeypatch.setattr(reader,'request',deleting);config(client,'D')
    _,_,token=grant_for(client,who,'Summarize document '+doc)
    result=call(client,token,doc)
    assert result['reason']=='DOCUMENT_UNAVAILABLE' and 'Private invoice' not in json.dumps(result)

def test_concurrent_document_reservations_never_exceed_owner_limit(client):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException
    from app.documents.repository import Repository
    repo=Repository(get_db(),'alice')
    def reserve(index):
        try: return repo.reserve('file.txt','text/plain',1,str(index))
        except HTTPException as exc:
            assert exc.status_code==409
            return None
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(reserve,range(25)))
    assert sum(result is not None for result in results)==20 and len(repo.list())==20

@pytest.mark.parametrize('model,vectors',[
    ('other-model',[[1.,1.]]),('test-model',[[1.]]),('test-model',[[float('nan'),1.]]),
    ('test-model',[[float('inf'),1.]]),('test-model',[[0.,0.]]),
])
def test_invalid_query_vectors_fail_closed(client,engines,monkeypatch,model,vectors):
    import asyncio
    from fastapi import HTTPException
    from app.documents import service
    doc=upload(client,login(client),b'Invoice amount 150000 VND.','invoice.txt').json()['id']
    async def invalid(texts): return model,vectors
    monkeypatch.setattr(service,'embed',invalid)
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.retrieve(get_db(),'alice',doc,'What amount?'))
    assert error.value.status_code==503

def test_legitimate_balance_output_after_document_read_still_uses_bank_facts(client,engines,monkeypatch):
    monkeypatch.setenv('ENV','demo')
    who=login(client);doc=upload(client,who,b'Invoice 150000 VND.','invoice.txt').json()['id'];config(client,'D')
    cid,_,token=grant_for(client,who,'Summarize document '+doc)
    assert call(client,token,doc)['decision']=='ALLOW'
    client.post('/api/agent/finish',headers=token,json={'answer':'Invoice summary','latency_ms':1})
    run=client.post('/api/agent/runs',headers=who,json={'conversation_id':cid,'content':'What is my balance?','profile':'defended'}).json()
    delegated={'Authorization':'Bearer '+run['delegated_token']}
    result=client.post('/api/agent/tools',headers=delegated,json={'name':'get_account_balance','arguments':{}}).json()
    assert result['decision']=='ALLOW'
    finish=client.post('/api/agent/finish',headers=delegated,json={'answer':'An unverified guess','latency_ms':1})
    assert finish.status_code==200 and format(result['result']['balance_vnd'],',') in finish.text
