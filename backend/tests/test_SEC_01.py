from tests.acceptance_helpers import *


def route_inventory(application):
    # Includes hidden routes and lazy included routers in the installed FastAPI.
    from fastapi.routing import _iter_routes_with_context
    inventory = set()
    for route, context in _iter_routes_with_context(application.routes):
        path = getattr(context, 'path', None) or route.path
        for method in getattr(route, 'methods', ()):
            inventory.add((method, path))
        if not hasattr(route, 'methods'):
            inventory.add(('MOUNT', path))
    return inventory


def matrix():
    return json.loads(Path(__file__).with_name('route_matrix.json').read_text(encoding='utf-8'))


def test_SEC_01_every_fastapi_route_has_an_explicit_matrix_entry():
    expected = {(r['method'], r['path']) for r in matrix()}
    optional = {(r['method'], r['path']) for r in matrix() if r.get('optional')}
    actual = route_inventory(app)
    assert not actual - expected, f'Unmapped routes: {actual - expected}'
    assert not expected - optional - actual, f'Missing required routes: {expected - optional - actual}'


def test_SEC_01_compiled_frontend_mount_is_explicitly_public(tmp_path):
    from fastapi import FastAPI
    from app.web import mount_frontend
    (tmp_path / 'index.html').write_text('<h1>Test UI</h1>', encoding='utf-8')
    frontend = FastAPI(); mount_frontend(frontend, tmp_path)
    assert route_inventory(frontend) <= {(r['method'], r['path']) for r in matrix()}


def test_SEC_01_inventory_detects_new_hidden_included_routes():
    from fastapi import FastAPI, APIRouter
    extra = FastAPI(); router = APIRouter(prefix='/hidden')
    router.add_api_route('/surprise', lambda: {}, include_in_schema=False)
    extra.include_router(router, prefix='/v2')
    assert ('GET', '/v2/hidden/surprise') in route_inventory(extra)
    assert route_inventory(extra) - {(r['method'], r['path']) for r in matrix()}


@pytest.mark.parametrize('role', ['anonymous', 'customer', 'support', 'operations', 'auditor', 'admin'])
def test_SEC_01_all_forbidden_route_role_pairs(client, monkeypatch, role):
    import re
    monkeypatch.setenv('RESEARCH_SANDBOX_ENABLED', 'true')
    who = {} if role == 'anonymous' else login(client, 'alice' if role == 'customer' else role)
    for entry in matrix():
        if role in entry['roles']:
            continue
        path = re.sub(r'\{[^}]+\}', 'missing', entry['path'])
        response = client.request(entry['method'], path, headers=who, json={} if entry['method'] in ('POST', 'PATCH', 'PUT') else None)
        assert response.status_code in (401, 403), (role, entry, response.status_code, response.text)


@pytest.mark.parametrize('enabled,expected', [('false', 403), ('true', 200)])
def test_SEC_01_research_admin_requires_explicit_sandbox(client, monkeypatch, tmp_path, enabled, expected):
    from app import routes_research
    monkeypatch.setattr(routes_research, 'REPORTS', tmp_path / 'reports')
    monkeypatch.setenv('RESEARCH_SANDBOX_ENABLED', enabled)
    who = login(client, 'admin')
    assert client.get('/api/research/runs', headers=who).status_code == expected


def test_SEC_01_support_alerts_are_own_security_only(client):
    customer = login(client)
    pay(client, customer, 12345)
    own = client.get('/api/notifications', headers=customer).json()['items']
    assert any(r['transaction_id'] for r in own)
    staff = login(client, 'support')
    from app.action_security import notify
    from app.database import now
    with get_db().connect() as conn:
        notify(conn, 'support', 'SECURITY', 'Profile updated', 'Your profile was updated.', now())
    response = client.get('/api/notifications', headers=staff)
    assert response.status_code == 200  # Explicit decision: own security alerts are safe.
    rows = response.json()['items']
    assert rows and all(r['owner_id'] == 'support' and r['transaction_id'] is None for r in rows)
    assert all(r['kind'] == 'SECURITY' for r in rows)
    target = next(r for r in own if r['transaction_id'])
    assert client.patch('/api/notifications/' + target['id'] + '/read', headers=staff).status_code == 404
    client.post('/api/notifications/read-all', headers=staff)
    assert next(r for r in client.get('/api/notifications', headers=customer).json()['items'] if r['id'] == target['id'])['read_at'] is None

@pytest.mark.parametrize('user,path,expected',[
    ('operations','/api/support/tickets',403),
    ('operations','/api/research/runs',403),
    ('auditor','/api/research/runs',403),
    ('support','/api/notifications',200),
])
def test_SEC_01_pdf_permission_matrix(client,user,path,expected):
    actual=client.get(path,headers=login(client,user)).status_code
    assert actual==expected, f'{user} GET {path}: {actual}; PDF expects {expected}'


def test_SEC_01_auditor_reads_customer_ticket(client):
    who=login(client)
    response=client.post('/api/support/tickets',headers=who,json={'subject':'Test ticket','description':'Audit access expectation'})
    assert response.status_code==201
    actual=client.get('/api/support/tickets/'+response.json()['id'],headers=login(client,'auditor')).status_code
    assert actual==404  # User ruling: auditor cannot read customer ticket contents.


def test_SEC_01_operations_can_freeze_account(client):
    actual=client.patch('/api/admin/accounts/ACC-ALICE-001',headers=login(client,'operations'),json={'status':'FROZEN'}).status_code
    assert actual==403  # User ruling: only admin may freeze/unfreeze accounts.


