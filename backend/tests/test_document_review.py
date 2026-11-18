"""Regression reproductions from the independent whole-branch review."""
import json
import pytest
from tests.acceptance_helpers import client, login, get_db  # noqa: F401
from tests.test_documents_api import engines, upload  # noqa: F401
from tests.test_documents_gateway import config, call
from tests.test_week7 import grant_for

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
