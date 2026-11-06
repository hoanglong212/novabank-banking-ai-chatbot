"""Mass assignment at every registered write boundary, with valid base schemas.

Server-owned extras may be ignored or rejected (PDF contract). Declared admin
status updates are legitimate inputs, not mass assignment.
"""
from tests.acceptance_helpers import *
from tests.agent_acceptance_helpers import run_for
from tests.test_SEC_01 import route_inventory
from fastapi.routing import _iter_routes_with_context
import re

EXTRAS = {'owner_id':'bob','status':'MASS_ASSIGN_SENTINEL','balance':999999999,'balance_vnd':999999999,'role':'admin'}
STATUS_INPUT = {'AccountState','Assignment','Document','FinishInput','UserState'}
SAMPLES = {
    'NotificationPreferences': {'bill_reminders':True,'budget_alerts':True},
    'RecipientLookup': {'account_id':'ACC-BOB-001','bank':'NovaBank'},
    'ProfileChange': {'field':'name','value':'Test name','password':'Alice@2026'},
    'Nickname': {'nickname':'Valid nickname'},
    'Beneficiary': {'account_id':'ACC-BOB-001','bank':'NovaBank','nickname':'Valid nickname'},
    'ActionConfirm': {'challenge_id':'a'*43,'code':'123456'},
    'ProductAction': {'kind':'FREEZE_CARD','resource_id':'CARD-ALICE-DEBIT'},
    'Budget': {'month':'2026-11','category':'Food','amount_vnd':1000},
    'Goal': {'label':'Goal','target_vnd':1000,'target_date':'2027-01-01'},
    'TicketInput': {'subject':'Valid ticket','description':'Valid description'},
    'Assignment': {'status':'OPEN'}, 'Reply': {'body':'Valid reply'},
    'Attachment': {'name':'hello.txt','content_base64':'aGVsbG8='},
    'UserState': {'status':'ACTIVE'}, 'AccountState': {'status':'ACTIVE'},
    'Settings': {'transfer_fee_vnd':0}, 'ScanInput': {'payload':'NBQR1.test'},
    'Document': {'title':'Valid policy','content':'Valid policy content','source':'Internal'},
    'PreviewInput': {'answer':'Balance overview'},
    'RunInput': {'conversation_id':'fixture','content':'What is my balance?'},
    'ToolInput': {'name':'get_accounts','arguments':{}},
    'FinishInput': {'answer':'Balance overview','latency_ms':1},
    'ApprovalInput': {'approve':False}, 'StreamInput': {'content':'What is my balance?'},
    'Launch': {'models':['qwen2.5:7b'],'smoke_test':True},
    'TransferArgs': {'to_account':'ACC-BOB-001','amount_vnd':1000},
    'TransferConfirm': {'otp':'123456'},
    'VietQRArgs': {'bank':'NovaBank','account_no':'ACC-ALICE-001'},
    'ConversationCreate': {'title':'Valid conversation'}, 'SendMessage': {'content':'What is my balance?'},
    'DemoToolCheck': {'tool_name':'get_account_balance','arguments':{}},
    'RegisterInput': {'username':'sec04','name':'Test user','email':'sec04@example.test','password':'Long test password 2026'},
    'EmailInput': {'email':'alice@novabank.test'}, 'TokenInput': {'token':'a'*43},
    'ResetInput': {'token':'a'*43,'password':'Long test password 2026'},
    'LoginRequest': {'username':'alice','password':'Alice@2026'},
    'VerifyInput': {'challenge_id':'a'*43,'code':'123456'},
    'ChallengeInput': {'challenge_id':'a'*43}, 'RefreshInput': {'refresh_token':'a'*43},
    'PasswordCheck': {'password':'Alice@2026'}, 'CodeInput': {'code':'123456'},
}
# Explicit inventory: additions without a reviewed test fail rather than silently skip.
BODYLESS = {
    ('DELETE','/api/customer/beneficiaries/{beneficiary_id}'),
    ('PATCH','/api/transactions/{transaction_id}/category'), ('DELETE','/api/savings-goals/{goal_id}'),
    ('PATCH','/api/bills/{bill_id}/saved'), ('POST','/api/admin/reconcile'), ('POST','/api/admin/knowledge-index'),
    ('POST','/api/agent/runs/{run_id}/cancel'), ('POST','/api/transfers/{transfer_id}/otp'),
    ('DELETE','/api/conversations/{conversation_id}'), ('PATCH','/api/notifications/{notification_id}/read'),
    ('POST','/api/notifications/read-all'), ('DELETE','/api/auth/sessions/{session_id}'),
    ('POST','/api/auth/logout'), ('POST','/api/auth/activity'),
}


def writes():
    result = []
    for route, context in _iter_routes_with_context(app.routes):
        for method in getattr(route,'methods',()):
            if method in ('POST','PUT','PATCH','DELETE'):
                result.append((method, getattr(context,'path',None) or route.path, route))
    return result


def protected():
    with get_db().connect() as conn:
        return [tuple(r) for r in conn.execute('SELECT id,owner_id,balance_vnd,status FROM accounts ORDER BY id')], [tuple(r) for r in conn.execute('SELECT id,role,status FROM users ORDER BY id')]


@pytest.mark.parametrize('method,path,route',writes(),ids=lambda v:v if isinstance(v,str) else '')
def test_SEC_04_each_write_endpoint_rejects_or_ignores_server_owned_extras(client, monkeypatch, method,path,route):
    who = login(client,'admin' if path.startswith(('/api/admin/','/api/research/')) else 'support' if path=='/api/support/tickets/{ticket_id}' else 'alice')
    monkeypatch.setenv('RESEARCH_SANDBOX_ENABLED','true')
    monkeypatch.setenv('LEGACY_AGENT_TEST_MODE','true')
    # Fail rather than launch an experiment if validation regresses.
    from app import routes_research
    monkeypatch.setattr(routes_research.subprocess, 'Popen', lambda *a,**k: pytest.fail('SEC-04 allowed a research launch'))
    fields = route.dependant.body_params
    before = protected()
    if fields:
        assert len(fields)==1
        model = fields[0].field_info.annotation
        assert model.__name__ in SAMPLES, 'Write schema needs an explicit valid baseline'
        sample = dict(SAMPLES[model.__name__])
        allowed = {'status'} if model.__name__ in STATUS_INPUT else set()
        assert set(model.model_fields)&set(EXTRAS) == allowed, 'Unexpected server-owned field became writable'
        model.model_validate(sample)  # Missing fields or invalid base types cannot make this probe pass.
        extra = {k:v for k,v in EXTRAS.items() if k not in allowed}
        if path.startswith('/api/agent/') and path in ('/api/agent/tools','/api/agent/finish','/api/agent/preview'):
            _,_,who = run_for(client,who)
        if model.model_config.get('extra') == 'forbid':
            url = re.sub(r'\{[^}]+\}','fixture',path)
            response = client.request(method,url,headers=who,json={**sample,**extra})
            assert response.status_code==422, (method,path,response.status_code)
            if isinstance(response.json()['detail'],list):
                assert {e['type'] for e in response.json()['detail']} == {'extra_forbidden'}
                assert {e['loc'][-1] for e in response.json()['detail']} == set(extra)
            assert protected()==before
            return
        assert model.model_config.get('extra') in (None,'ignore')
        assert model.model_validate({**sample,**extra}).model_dump() == model.model_validate(sample).model_dump()
        if model.__name__ in ('SendMessage','DemoToolCheck','ConversationCreate'):
            cid = client.post('/api/conversations',headers=who,json={'title':'Fixture'}).json()['id']
            path = path.replace('{conversation_id}',cid)
        if model.__name__=='TransferConfirm':
            draft = client.post('/api/transfers',headers=who,json=SAMPLES['TransferArgs']).json()
            path=path.replace('{transfer_id}',draft['id']);sample['otp']=transfer_code(draft)
        response = client.request(method,path,headers=who,json={**sample,**extra})
        assert response.status_code in (200,201,202), (path,response.status_code)
        after=protected()
        if model.__name__=='TransferConfirm':
            assert after[1]==before[1]
            assert [(r[0],r[1],r[3]) for r in after[0]]==[(r[0],r[1],r[3]) for r in before[0]]
            assert after[0][0][2]==before[0][0][2]-1000 and after[0][1][2]==before[0][1][2]+1000
        else:
            assert after==before
        with get_db().connect() as conn:
            assert not conn.execute("SELECT 1 FROM conversations WHERE owner_id='bob'").fetchone()
    else:
        assert (method,path) in BODYLESS, 'Unreviewed bodyless write route'
        # These routes take parameters from path/query, never from an extra JSON body.
        params={}
        if '{beneficiary_id}' in path:
            path=path.replace('{beneficiary_id}',beneficiary(client,who)['id'])
        elif '{transaction_id}' in path:
            path=path.replace('{transaction_id}','TX-1001');params={'category':'food'}
        elif '{goal_id}' in path:
            goal=client.post('/api/savings-goals',headers=who,json=SAMPLES['Goal'])
            assert goal.status_code==201
            path=path.replace('{goal_id}',goal.json()['id'])
        elif '{bill_id}' in path:
            bill=client.get('/api/products/bills',headers=who).json()['items'][0]['id']
            path=path.replace('{bill_id}',bill);params={'saved':'true'}
        elif '{run_id}' in path:
            _,grant,_=run_for(client,who);path=path.replace('{run_id}',grant['run_id'])
        elif '{transfer_id}' in path:
            draft=client.post('/api/transfers',headers=who,json=SAMPLES['TransferArgs']).json()
            path=path.replace('{transfer_id}',draft['id'])
        elif '{conversation_id}' in path:
            cid=client.post('/api/conversations',headers=who,json={'title':'Delete fixture'}).json()['id']
            path=path.replace('{conversation_id}',cid)
        elif '{notification_id}' in path:
            from app.action_security import notify
            from app.database import now
            with get_db().connect() as conn:
                notify(conn,'alice','SECURITY','Fixture','Own security alert',now())
                key=conn.execute("SELECT id FROM service_notifications WHERE owner_id='alice' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            path=path.replace('{notification_id}',key)
        elif '{session_id}' in path:
            sid=client.get('/api/auth/sessions',headers=who).json()['items'][0]['id']
            path=path.replace('{session_id}',sid)
        elif path=='/api/admin/knowledge-index':
            # This probe exercises mass assignment, not a live Ollama installation.
            # Keep authorization/index writes real and isolate only model inference.
            from app import knowledge
            async def fixture_embeddings(texts):
                return 'sec04-fixture', [[1.0, 0.0] for _ in texts]
            monkeypatch.setattr(knowledge, 'embed', fixture_embeddings)
        response=client.request(method,path,params=params,headers=who,json=EXTRAS)
        assert response.status_code in (200,204), (method,path,response.status_code)
        if path=='/api/admin/knowledge-index':
            assert response.json()['indexed_documents'] > 0
            assert response.json()['indexed_chunks'] > 0
        assert protected()==before


def test_SEC_04_write_inventory_includes_hidden_routes():
    expected={(m,p) for m,p in route_inventory(app) if m in ('POST','PUT','PATCH','DELETE')}
    assert {(m,p) for m,p,_ in writes()}==expected

from tests.conftest import transfer_code
