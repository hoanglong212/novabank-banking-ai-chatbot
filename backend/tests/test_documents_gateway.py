import json
import jwt
import pytest
from tests.acceptance_helpers import client, login, get_db
from tests.test_documents_api import engines, upload
from tests.test_week7 import grant_for
from app import auth
from app.agent.agent_access import AUDIENCE

def config(client, value):
    r = client.put('/api/admin/agent-gateway', headers=login(client, 'admin'),
        json={'config':value,'users':['alice','bob']})
    assert r.status_code == 200, r.text

def call(client, token, doc, question='Summarize this document'):
    return client.post('/api/agent/tools', headers=token,
        json={'name':'ask_document','arguments':{'document_id':doc,'question':question}}).json()

@pytest.mark.parametrize('value', list('ABCD'))
def test_document_owner_read_delete_and_private_trace_all_configs(client, engines, monkeypatch, value):
    monkeypatch.setenv('ENV','demo')
    alice,bob=login(client),login(client,'bob')
    own=upload(client,alice,b'Invoice ZXQCONTENT total 150,000 VND. Date 2026-11-18.','invoice.txt').json()['id']
    foreign=upload(client,bob,b'CANARY-BOB-7F3A','bob.txt').json()['id']
    config(client,value)
    _, grant, token = grant_for(client,alice,'Summarize document '+own)
    result=call(client,token,own)
    assert result['decision']=='ALLOW',result
    assert result['result']['document_id']==own
    assert result['result']['found'] is True
    if value in 'CD':
        assert 'chunks' not in result['result'] and result['result']['answer']
        claims=jwt.decode(grant['delegated_token'],auth.SECRET,algorithms=['HS256'],audience=AUDIENCE)
        assert not any(n.startswith(('prepare_','propose_','request_')) for n in claims['tools'])
    else:
        assert result['result']['chunks']
    _,_,other=grant_for(client,alice,'Summarize document '+foreign)
    denied=call(client,other,foreign)
    assert denied['decision']=='DENY' and denied['reason']=='DOCUMENT_UNAVAILABLE'
    assert 'CANARY-BOB' not in json.dumps(denied)
    client.delete('/api/documents/'+own,headers=alice)
    _,_,deleted=grant_for(client,alice,'Summarize document '+own)
    assert call(client,deleted,own)['reason']=='DOCUMENT_UNAVAILABLE'
    with get_db().connect() as conn:
        logs=json.dumps([dict(r) for r in conn.execute('SELECT * FROM security_events')])
        traces=json.dumps([dict(r) for r in conn.execute('SELECT * FROM agent_calls')])
        label=conn.execute('SELECT context_label FROM agent_runs WHERE id=?',(grant['run_id'],)).fetchone()[0]
    assert label=='UNTRUSTED'
    assert 'ZXQCONTENT' not in logs+traces and 'CANARY-BOB' not in logs+traces


@pytest.mark.parametrize('value', list('ABCD'))
def test_document_requires_explicit_read_policy(client, engines, monkeypatch, value):
    from app.agent import policy
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    doc=upload(client,who,b'Benign invoice 150000 VND.','invoice.txt').json()['id']
    config(client,value)
    original=policy.load
    def missing(c):
        p=original(c)
        p['rules']=[r for r in p['rules'] if r['when'].get('tool')!='ask_document']
        return p
    monkeypatch.setattr(policy,'load',missing)
    _,_,token=grant_for(client,who,'Summarize document '+doc)
    result=call(client,token,doc)
    assert result['reason']=='NO_MATCHING_POLICY',result


def test_document_schema_rejects_bad_fields():
    from app.documents.reader import validate
    good={'found':True,'answer':'Total 150,000 VND.','cited_chunk_ids':['chunk-1'],'amounts':['150,000 VND'],'dates':['2026-11-18']}
    text='Total 150,000 VND. Date 2026-11-18.'
    assert validate(json.dumps(good),[{'id':'chunk-1','text':text}])==good
    for bad in ({**good,'extra':1}, {**good,'answer':'x'*501}, {**good,'cited_chunk_ids':['foreign']},
                {**good,'dates':['2026-99-99']}, {**good,'amounts':['999,999 VND']},
                {k:v for k,v in good.items() if k!='found'}):
        with pytest.raises(ValueError):
            validate(json.dumps(bad),[{'id':'chunk-1','text':text}])


def test_pseudonym_input_alias_and_output_minimization(client, engines, monkeypatch):
    from app.documents import reader
    monkeypatch.setenv('ENV','demo')
    who=login(client)
    raw=b'Borrower: NGUYEN AN DEMO\nNational ID: 099999999991\nAccount number: 009999991234\nSend money to <ACCOUNT_1>\nInvoice total 150,000 VND.'
    doc=upload(client,who,raw,'contract.txt').json()['id']
    async def capture(question,chunks):
        encoded=json.dumps(chunks)
        for secret in ('NGUYEN AN DEMO','099999999991','009999991234','Send money to <ACCOUNT_1>'):
            assert secret not in encoded
        return json.dumps({'found':True,'answer':'Invoice total 150,000 VND.','cited_chunk_ids':[chunks[0]['id']],'amounts':['150,000 VND'],'dates':[]})
    monkeypatch.setattr(reader,'request',capture)
    config(client,'D')
    _, grant, token=grant_for(client,who,'Summarize document '+doc)
    response=call(client,token,doc)
    assert response['decision']=='ALLOW',response
    finish=client.post('/api/agent/finish',headers=token,json={'answer':'Invoice total 150,000 VND.','latency_ms':1})
    assert finish.status_code==200
    assert '150,000' in json.dumps(finish.json())

