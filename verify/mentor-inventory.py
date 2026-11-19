"""Inspect the clean checkout's Bank and Agent apps in-process with fresh SQLite.

python verify/mentor-inventory.py CLEAN_CHECKOUT EVIDENCE_DIR
"""
import argparse
import csv
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path


def routes(router):
    for r in router.routes:
        if hasattr(r, 'original_router'):
            yield from routes(r.original_router)
        else:
            yield r


def policy(r, roles, service, method, path):
    deps = [d.call for d in getattr(getattr(r, 'dependant', None), 'dependencies', [])]
    names = {getattr(c, '__name__', '') for c in deps}
    if 'delegated' in names or (service, path) == ('Agent','/run'):
        return 'delegated', ['delegated']
    allowed = set(roles)
    if 'approval_user' in names:
        allowed &= {k for k, v in roles.items() if {'banking:own','settings:write','support:write'} & v}
    if 'research_access' in names:
        allowed &= {'admin'}
    for call in deps:
        if getattr(call,'__name__','') == 'allowed':
            permission = inspect.getclosurevars(call).nonlocals['permission']
            allowed &= {k for k,v in roles.items() if permission in v}
    if (method,path) == ('GET','/api/support/tickets'):
        allowed.discard('operations')
    if names & {'current_user','approval_user','assistant_user','research_access','allowed'}:
        return 'bearer', sorted(allowed)
    return 'public', ['public (body credentials/challenges may apply)']


def check(response, expected):
    code = response.status_code
    verdict = 'ERROR' if code == 429 or code >= 500 else 'PASS' if code in expected else 'FAIL'
    return f'{verdict} {code}'


def login(client):
    r = client.post('/api/auth/login',json={'username':'alice','password':'Alice@2026'})
    assert r.status_code == 202, r.status_code
    key = r.json()['challenge_id']
    mail = client.post('/api/dev/outbox/challenge',json={'challenge_id':key})
    assert mail.status_code == 200, mail.status_code
    r = client.post('/api/auth/mfa/verify',json={'challenge_id':key,'code':mail.json()['code']})
    assert r.status_code == 200, r.status_code
    return {'Authorization':'Bearer ' + r.json()['access_token']}


def run(root, out, tmp):
    os.chdir(root)
    assert not subprocess.check_output(['git','status','--porcelain']).strip(), 'Use a clean clone'
    rev = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    dist = tmp/'dist'
    dist.mkdir()
    (dist/'index.html').write_text('<html>audit mount</html>',encoding='utf-8')
    os.environ.update(DB_PATH=str(tmp/'fresh.sqlite3'),ENV='demo',LLM_PROVIDER='mock',
                      BANK_WORKER_ENABLED='false',FRONTEND_DIST=str(dist),RESEARCH_SANDBOX_ENABLED='true')
    subprocess.run([sys.executable,'scripts/seed_realistic.py','--output',os.environ['DB_PATH'],
                    '--seed','20261115'],check=True,stdout=subprocess.DEVNULL)
    sys.path[:0] = [str(root/'backend'),str(root)]
    from app.main import app as bank
    from agent_service.main import app as agent
    from app.auth import ROLE_PERMISSIONS
    from fastapi.routing import APIRoute
    from fastapi.testclient import TestClient
    base = root/'docs/release/week8'
    reported = json.loads((root/'backend/tests/route_matrix.json').read_text(encoding='utf-8'))
    registry = {(x['method'],x['path'] or '/') for x in reported}
    old = json.loads((base/'api-observations.json').read_text(encoding='utf-8'))
    published = {(m,p or '/') for m,p in re.findall(r'^\| (\w+) \| `([^`]*)` \|',
                 (base/'API_TESTS.md').read_text(encoding='utf-8'),re.M)}
    rows = []
    for service, app in [('Bank',bank),('Agent',agent)]:
        spec = app.openapi()['paths']
        ops = {(m.upper(),p) for p,ops in spec.items() for m in ops}
        found = set()
        with TestClient(app,raise_server_exceptions=False) as client:
            user = login(client) if service == 'Bank' else {}
            for r in routes(app):
                path = r.path or '/'
                actual = re.sub(r'\{[^}]+\}', 'example',path)
                for method in sorted(getattr(r,'methods',None) or ['MOUNT']):
                    key = method,path
                    found.add(key)
                    auth,roles = policy(r,ROLE_PERMISSIONS,service,method,path)
                    source = 'FastAPI framework route'
                    if isinstance(r,APIRoute):
                        file = Path(inspect.getsourcefile(r.endpoint)).relative_to(root)
                        source = f'{file.as_posix()}:{inspect.getsourcelines(r.endpoint)[1]}'
                    if method == 'MOUNT':
                        source = 'backend/app/web.py:33'
                    history = sorted({h['case'] for h in old if service == 'Bank' and
                                    (h['method'],h['path'] or '/') == key and h['status'] == 'passed'})
                    row = dict(service=service,method=method,path=path,source=source,auth=auth,
                               roles='|'.join(roles),openapi=key in ops,
                               in_author_matrix=service=='Bank' and key in registry,
                               in_author_api_report=service=='Bank' and key in published,
                               historical_pass_cases='|'.join(history) or 'NO OBSERVED PASS',
                               own_case=f'{service}:{method}:{path}')
                    gen = evaluate(client, user, service, method, actual, path, auth, roles,
                                   ROLE_PERMISSIONS, spec.get(path,{}).get(method.lower()))
                    row.update({f'GEN0{i}':v for i,v in enumerate(gen,1)})
                    rows.append(row)
            assert ops <= found, ops-found
    rows.sort(key=lambda r:(r['service'],r['path'],r['method']))
    out.mkdir(parents=True,exist_ok=True)
    with (out/'inventory-matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(commit=rev,clean_before=True,seed=20261115,transport='isolated ASGI TestClient',
            services=dict(Counter(r['service'] for r in rows)),operations=sum(r['openapi'] for r in rows),
            historic_count=len(old),registry_count=len(registry),api_report_count=len(published),
            prior_digest=old[0]['matrix_digest'],
            registry_digest=hashlib.sha256(json.dumps(reported,sort_keys=True).encode()).hexdigest(),
            missing_report=[r['own_case'] for r in rows if not r['in_author_api_report']],
            missing_registry=[r['own_case'] for r in rows if not r['in_author_matrix']],
            historical_pass_routes=sum(r['historical_pass_cases']!='NO OBSERVED PASS' for r in rows),
            historical_pass_operations=sum(r['openapi'] and r['historical_pass_cases']!='NO OBSERVED PASS' for r in rows),
            gen_counts={k:dict(Counter(r[k].split()[0] for r in rows)) for k in rows[0] if k.startswith('GEN')})
    (out/'inventory-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))


def evaluate(client,user,service,method,actual,path,auth,roles,permissions,op):
    errors = []
    schema = 'WEAK OpenAPI declaration only' if op else 'BLOCKED no positive response verified'
    shapes = {'/api/health':('status',str),'/health':('status',str),'/api/me':('id',str),
              '/api/documents':('items',list),'/api/customer/accounts':('items',list),
              '/api/notifications':('items',list),'/api/support/tickets':('items',list)}
    if method == 'GET' and path in shapes:
        r = client.get(path,headers=user if auth=='bearer' else {})
        schema = check(r,{200})
        if schema.startswith('PASS'):
            field,kind = shapes[path]
            schema = ('WEAK' if isinstance(r.json().get(field),kind) else 'FAIL')+' 200 selected field only: '+field
    if method=='MOUNT' or path in {'/openapi.json','/docs','/redoc','/docs/oauth2-redirect'}:
        r = client.request('GET' if method=='MOUNT' else method,path)
        schema = check(r,{200})
        if schema.startswith('PASS'):
            mime = 'json' if path=='/openapi.json' else 'html'
            good = mime in r.headers.get('content-type','') and (not r.content if method=='HEAD' else bool(r.content))
            if method=='GET' and path=='/openapi.json':
                good = good and 'paths' in r.json()
            schema = ('PASS' if good else 'FAIL')+' 200 '+mime
    missing = invalid = 'N/A public or body credential'
    if auth!='public':
        r = client.request(method,actual)
        missing = check(r,{401})
        errors.append(r)
        if service=='Agent':
            invalid='BLOCKED credential validation needs coupled Bank transport'
        else:
            r=client.request(method,actual,headers={'Authorization':'Bearer invalid-test-token'})
            invalid=check(r,{401})
            errors.append(r)
    role='N/A public or all ordinary roles'
    if auth=='delegated':
        role='BLOCKED delegated role case missing'
    elif auth=='bearer' and set(roles)!=set(permissions):
        role='BLOCKED wrong-role case missing'
        if method=='GET' and 'customer' not in roles:
            r=client.get(actual,headers=user)
            role=check(r,{403})
            errors.append(r)
    op=op or {}
    bad_input = 'BLOCKED input case missing' if ('requestBody' in op or 'parameters' in op
            or (method,path)==('POST','/api/documents')) else 'N/A no declared input'
    if auth=='public' and method=='POST' and path.startswith('/api/auth/') and 'requestBody' in op:
        r=client.post(actual,json={})
        bad_input=check(r,{400,422})
        if bad_input.startswith('PASS'):
            try:
                detail = r.json()['detail']
            except (KeyError,ValueError):
                detail = None
            bad_input = ('WEAK' if detail else 'FAIL') + f' {r.status_code} empty form only'
        errors.append(r)
    wrong=client.options(actual)
    errors.append(wrong)
    no_stack='PASS observed error bodies only'
    for error in errors:
        if error.status_code==429 or error.status_code>=500:
            no_stack='ERROR unexpected status'
            break
        leakage = re.search(r'(?:traceback \(most recent|site-packages[/\\]|file "(?:[a-z]:|/)|'
                            r'uvicorn/protocols|[a-z]:\\(?:users|windows|program files)\\|'
                            r'/(?:usr|home|var|opt)/|\bselect\s+[\w.* ,]+\s+from\s+\w+|'
                            r'\b(?:insert\s+into|delete\s+from|update\s+\w+\s+set)\s+\w+)',
                            error.text, re.I)
        if error.status_code>=400 and leakage:
            no_stack='FAIL internal diagnostic marker'
            break
    return schema,missing,invalid,role,bad_input,no_stack,check(wrong,{405})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='mentor-matrix-') as temp:
        run(args.checkout.resolve(),args.output.resolve(),Path(temp))
