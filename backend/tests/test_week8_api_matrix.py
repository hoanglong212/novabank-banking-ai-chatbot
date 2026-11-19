"""Actual TestClient authorization cases with real owned resources, not missing IDs."""
import base64
import importlib
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
from tests.acceptance_helpers import client, login, get_db, pytest
from tests.conftest import transfer_code
from tests.test_AI_12 import run_for

APP = importlib.import_module('app.main')
PROJECT = Path(APP.__file__).resolve().parents[2]
MATRIX = json.loads((PROJECT / 'backend/tests/route_matrix.json').read_text(encoding='utf-8'))
EVIDENCE = Path(os.environ.get('W8_API_EVIDENCE', str(Path(__file__).resolve().parents[2] / '.local/week8-api/observations.jsonl')))
RUN = uuid.uuid4().hex
MATRIX_DIGEST = hashlib.sha256(json.dumps(MATRIX, sort_keys=True).encode()).hexdigest()


def record(entry, case, status, *, expected=None, reason='', concrete_path=None, **extra):
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    value = {'run': RUN, 'matrix_digest': MATRIX_DIGEST, 'runtime_source': str(PROJECT), 'method': entry['method'], 'path': entry['path'], 'scope': entry.get('scope'),
        'case': case, 'status': status, 'expected': expected, 'reason': reason,
        'concrete_path': concrete_path, **extra}
    with EVIDENCE.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')


def check(response, expected):
    return response.status_code in expected


@pytest.fixture
def owned(client, monkeypatch):
    return prepare_owned_resources(client, monkeypatch)


def prepare_owned_resources(client, monkeypatch):
    monkeypatch.setenv('ENV', 'demo')
    monkeypatch.setenv('LEGACY_AGENT_TEST_MODE', 'true')
    monkeypatch.setenv('RESEARCH_SANDBOX_ENABLED', 'true')
    alice, bob = login(client), login(client, 'bob')
    from app.auth_crypto import totp
    setup = client.post('/api/auth/mfa/setup', headers=alice, json={'password': 'Alice@2026'})
    assert setup.status_code == 200, setup.text
    secret = setup.json()['secret']
    enabled = client.post('/api/auth/mfa/enable', headers=alice, json={'code': totp(secret, int(time.time()) // 30 - 1)})
    assert enabled.status_code == 200, enabled.text
    bills = client.get('/api/products/bills', headers=alice).json()['items']
    cards = client.get('/api/products/cards', headers=alice).json()['items']
    card = next(c for c in cards if c['kind'] == 'DEBIT')['id']
    person = client.post('/api/customer/beneficiaries', headers=alice,
        json={'account_id': 'ACC-BOB-001', 'bank': 'NovaBank', 'nickname': 'C5 synthetic recipient'})
    assert person.status_code == 201, person.text
    with get_db().connect() as conn:
        conn.execute("DELETE FROM verified_payees WHERE owner_id='alice' AND to_account='ACC-BOB-001' AND origin='fixture_known'")
    transfer = client.post('/api/transfers', headers=alice,
        json={'to_account': 'ACC-BOB-001', 'amount_vnd': 1000, 'content': 'C5 authorized fixture'})
    assert transfer.status_code == 201, transfer.text
    transfer_id = transfer.json()['id']
    stepup = client.post('/api/transfers/' + transfer_id + '/step-up', headers=alice, json={'code': totp(secret, int(time.time()) // 30)})
    assert stepup.status_code == 200, stepup.text
    assert stepup.json()['required'] and stepup.json()['verified'], stepup.text
    client.post('/api/auth/pin', headers=alice, json={'password': 'Alice@2026', 'pin': '482916'}).raise_for_status()
    assert client.post('/api/transfers/' + transfer_id + '/otp', headers=alice).status_code == 200
    code = transfer_code({'id': transfer_id})
    completed = client.post('/api/transfers/' + transfer_id + '/confirm', headers={**alice, 'Idempotency-Key': 'c5-fixture-once'}, json={'otp': code})
    assert completed.status_code == 200, completed.text
    pending = client.post('/api/transfers', headers=alice,
        json={'to_account': 'ACC-BOB-001', 'amount_vnd': 2000, 'content': 'C5 pending fixture'})
    assert pending.status_code == 201
    pending = pending.json()
    ticket = client.post('/api/support/tickets', headers=alice,
        json={'subject': 'C5 owned resource', 'description': 'A fictional support issue for the authorization audit.'})
    assert ticket.status_code == 201
    ticket_id = ticket.json()['id']
    attachment = client.post(f'/api/support/tickets/{ticket_id}/attachments', headers=alice,
        json={'name': 'audit.txt', 'content_base64': base64.b64encode(b'C5 synthetic attachment').decode()})
    assert attachment.status_code == 201, attachment.text
    goal = client.post('/api/savings-goals', headers=alice,
        json={'label': 'C5 owned goal', 'target_vnd': 100000, 'target_date': '2035-01-01'})
    assert goal.status_code == 201
    action = client.post('/api/products/actions', headers=alice, json={'kind': 'FREEZE_CARD', 'resource_id': card})
    assert action.status_code == 202
    cid, grant, delegated = run_for(client, alice, 'Create a support ticket: please review this fictional card issue')
    proposal = client.post('/api/agent/tools', headers=delegated, json={'name': 'prepare_support_ticket',
        'arguments': {'subject': 'C5 proposal', 'description': 'A fictional card issue'}})
    assert proposal.status_code == 200 and proposal.json()['decision'] == 'ALLOW', proposal.text
    _, bob_grant, bob_delegated = run_for(client, bob, 'What is my balance?')
    sessions = client.get('/api/auth/sessions', headers=alice).json()
    sessions = sessions.get('items', sessions) if isinstance(sessions, dict) else sessions
    notifications = client.get('/api/notifications', headers=alice).json()['items']
    with get_db().connect() as conn:
        message = conn.execute("SELECT id FROM dev_outbox WHERE user_id='alice' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    fixture = {'alice': alice, 'bob': bob, 'delegated': delegated, 'bob_delegated': bob_delegated,
        'cid': cid, 'run_id': grant['run_id'], 'bob_run_id': bob_grant['run_id'],
        'account_id': 'ACC-ALICE-001', 'beneficiary_id': person.json()['id'], 'card_id': card,
        'transfer_id': pending['id'], 'confirm_token': pending.get('confirm_token', ''),
        'completed_transfer_id': transfer_id, 'completed': completed.json(), 'completed_otp': code,
        'transaction_id': completed.json()['transaction_id'], 'ticket_id': ticket_id,
        'attachment_id': attachment.json()['id'], 'goal_id': goal.json()['id'], 'bill_id': bills[0]['id'],
        'approval_id': proposal.json()['result']['approval_id'], 'challenge_id': action.json()['challenge_id'],
        'session_id': sessions[0]['id'], 'message_id': message, 'notification_id': notifications[0]['id']}
    return fixture


def concrete(entry, owned):
    values = {**owned, 'kind': 'cards', 'fmt': 'csv', 'document_id': 'KB-savings', 'user_id': 'alice',
        'filename': 'results.csv', 'source_id': 'tx:TX-1001', 'conversation_id': owned['cid']}
    return re.sub(r'\{([^}]+)\}', lambda m: str(values.get(m.group(1), 'C5-UNUSED-SELECTOR')), entry['path'])


def request_parts(entry, owned):
    path = concrete(entry, owned); params = {}; body = None
    if path.endswith('/category'): params = {'category': 'other'}
    elif path.endswith('/saved'): params = {'saved': 'true'}
    elif path == '/api/insights': params = {'month': '2026-11'}
    elif path.startswith('/api/statements.'): params = {'from_date': '2026-01-01', 'to_date': '2026-11-15'}
    elif path in ('/api/agent/runs', '/api/agent/approvals') and entry['method'] == 'GET': params = {'conversation_id': owned['cid']}
    elif path == '/api/knowledge/search': params = {'query': 'savings'}
    if entry['method'] in ('POST', 'PUT', 'PATCH'):
        body = {}
        if '/customer/accounts/' in path or '/customer/beneficiaries/' in path and entry['method'] == 'PATCH': body = {'nickname': 'C5 renamed'}
        elif '/savings-goals/' in path or path == '/api/savings-goals': body = {'label': 'C5 goal', 'target_vnd': 200000, 'target_date': '2035-01-01'}
        elif path.endswith('/attachments'): body = {'name': 'audit.txt', 'content_base64': base64.b64encode(b'C5 synthetic').decode()}
        elif '/support/tickets/' in path and path.endswith('/messages'): body = {'body': 'C5 synthetic reply'}
        elif path.endswith('/confirm') and '/transfers/' in path: body = {'otp': '000000', 'confirm_token': owned['confirm_token']}
        elif path.endswith('/step-up'): body = {'code': '000000'}
        elif path == '/api/actions/confirm': body = {'challenge_id': owned['challenge_id'], 'code': '000000'}
        elif path == '/api/agent/runs': body = {'conversation_id': owned['cid'], 'content': 'What is my balance?'}
        elif path == '/api/agent/tools': body = {'name': 'get_account_balance', 'arguments': {}}
        elif path == '/api/agent/preview': body = {'answer': 'C5 response'}
        elif path == '/api/agent/finish': body = {'answer': 'C5 response', 'latency_ms': 1}
        elif '/agent/approvals/' in path: body = {'approve': False}
        elif path.endswith('/stream') or path.endswith('/messages') and '/conversations/' in path: body = {'content': 'What is my balance?'}
        elif path.endswith('/demo/tool-check'): body = {'tool_name': 'get_account_balance', 'arguments': {}}
    return path, params, body


def test_every_protected_route_rejects_anonymous_call_on_real_resource_paths(client, owned):
    failures = []
    for entry in MATRIX:
        protected = 'anonymous' not in entry['roles'] or entry['path'] in ('/api/dev/outbox', '/api/dev/outbox/{message_id}')
        if not protected or entry['method'] == 'MOUNT':
            record(entry, 'anonymous', 'not_applicable', reason='Public/static/challenge-authenticated surface, not bearer protected')
            continue
        path, params, body = request_parts(entry, owned)
        response = client.request(entry['method'], path, params=params, json=body)
        passed = check(response, (401, 403))
        record(entry, 'anonymous', 'passed' if passed else 'failed', expected=[401, 403], concrete_path=path, actual=response.status_code)
        if not passed: failures.append((entry['method'], entry['path'], response.status_code))
    assert not failures, failures


def test_cross_owner_existing_resources_and_implicit_identity_scopes(client, owned):
    failures = []
    owned_selectors = {'account_id', 'beneficiary_id', 'transaction_id', 'goal_id', 'bill_id', 'ticket_id',
        'attachment_id', 'approval_id', 'conversation_id', 'transfer_id', 'notification_id', 'session_id', 'message_id'}
    for entry in MATRIX:
        selectors = set(re.findall(r'\{([^}]+)\}', entry['path']))
        private_selector = selectors & owned_selectors or selectors == {'run_id'} and entry['path'].startswith('/api/agent/')
        if 'customer' not in entry['roles'] or entry.get('scope') in ('staff', 'sandbox-enabled', 'public', 'compiled-frontend-only'):
            record(entry, 'cross_owner', 'not_applicable', reason='Global/public or privileged staff surface; role checks apply instead')
            continue
        if not private_selector:
            record(entry, 'cross_owner', 'not_applicable', reason='No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared')
            continue
        path, params, body = request_parts(entry, owned)
        response = client.request(entry['method'], path, headers=owned['bob'], params=params, json=body)
        passed = check(response, (403, 404))
        record(entry, 'cross_owner', 'passed' if passed else 'failed', expected=[403, 404], concrete_path=path,
            actual=response.status_code, owner='alice', actor='bob', resource_exists=True)
        if not passed: failures.append((entry['method'], entry['path'], response.status_code, response.text[:120]))
    assert not failures, failures


def test_owned_resource_positive_controls_and_replay_do_not_move_money_twice(client, owned):
    paths = [f'/api/support/tickets/{owned["ticket_id"]}', f'/api/support/attachments/{owned["attachment_id"]}',
        f'/api/transfers/{owned["transfer_id"]}', f'/api/transactions/{owned["transaction_id"]}',
        f'/api/transactions/{owned["transaction_id"]}/receipt.pdf', f'/api/agent/runs/{owned["run_id"]}',
        f'/api/agent/approvals/{owned["approval_id"]}', f'/api/conversations/{owned["cid"]}/messages',
        f'/api/dev/outbox/{owned["message_id"]}']
    for path in paths:
        response = client.get(path, headers=owned['alice'])
        assert response.status_code == 200, (path, response.status_code, response.text[:100])
        matching = next((entry for entry in MATRIX if entry['method'] == 'GET' and concrete(entry, owned) == path), None)
        if matching:
            record(matching, 'owner_positive_control', 'passed', actual=200, concrete_path=path, resource_exists=True)
    with get_db().connect() as conn:
        before = conn.execute("SELECT balance_vnd FROM accounts WHERE id='ACC-ALICE-001'").fetchone()[0]
    replay = client.post('/api/transfers/' + owned['completed_transfer_id'] + '/confirm', headers={**owned['alice'], 'Idempotency-Key': 'c5-fixture-once'}, json={'otp': owned['completed_otp']})
    assert replay.status_code == 200 and replay.json() == owned['completed']
    denied = client.post('/api/transfers/' + owned['completed_transfer_id'] + '/confirm', headers={**owned['alice'], 'Idempotency-Key': 'c5-different-key'}, json={'otp': owned['completed_otp']})
    assert denied.status_code in (400, 409)
    with get_db().connect() as conn:
        assert conn.execute("SELECT balance_vnd FROM accounts WHERE id='ACC-ALICE-001'").fetchone()[0] == before
    entry = next(e for e in MATRIX if e['path'] == '/api/transfers/{transfer_id}/confirm')
    record(entry, 'replay', 'passed', reason='Same key returns original receipt; different key rejected; balances unchanged')


def test_body_bound_owner_targets_and_delegated_identity_are_enforced(client, owned):
    probes = [('/api/products/actions', {'kind': 'FREEZE_CARD', 'resource_id': owned['card_id']}, (404,)),
        ('/api/actions/confirm', {'challenge_id': owned['challenge_id'], 'code': '000000'}, (404,)),
        ('/api/agent/runs', {'conversation_id': owned['cid'], 'content': 'What is my balance?'}, (404,)),
        ('/api/transfers', {'from_account': 'ACC-ALICE-001', 'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 1000}, (400,))]
    for path, body, expected in probes:
        response = client.post(path, headers={**owned['bob'], 'Idempotency-Key': 'c5-foreign-probe'}, json=body)
        assert response.status_code in expected, (path, response.status_code, response.text)
        if path == '/api/transfers': assert response.json()['detail'] == 'ACCOUNT_NOT_OWNED'
        entry = next(e for e in MATRIX if e['method'] == 'POST' and e['path'] == path)
        record(entry, 'cross_owner_body', 'passed', concrete_path=path, actual=response.status_code, resource_exists=True)
    context = client.get('/api/agent/context?run_id=' + owned['run_id'], headers=owned['bob_delegated'])
    assert context.status_code == 200 and context.json()['run_id'] == owned['bob_run_id']
    denied = client.post('/api/agent/tools', headers=owned['bob_delegated'], json={'name': 'get_account_balance', 'arguments': {'account_id': 'ACC-ALICE-001'}})
    assert denied.status_code == 200 and denied.json()['decision'] == 'DENY'
    allowed = client.post('/api/agent/tools', headers=owned['bob_delegated'], json={'name': 'get_account_balance', 'arguments': {}})
    assert allowed.status_code == 200 and allowed.json()['decision'] == 'ALLOW'
    for entry in [e for e in MATRIX if e.get('scope') == 'run-owner-session']:
        path, params, body = request_parts(entry, owned)
        response = client.request(entry['method'], path, headers=owned['alice'], params=params, json=body)
        assert response.status_code in (401, 403), (entry, response.status_code)
        record(entry, 'ordinary_token_on_delegated_route', 'passed', actual=response.status_code,
            reason='Normal banking JWT cannot impersonate a delegated run capability')


def test_forbidden_role_pairs_are_rejected_without_dto_false_positives(client, owned):
    failures = []
    for role in ('customer', 'support', 'operations', 'auditor', 'admin'):
        who = owned['alice'] if role == 'customer' else login(client, role)
        for entry in MATRIX:
            if role in entry['roles'] or entry['method'] == 'MOUNT': continue
            path, params, body = request_parts(entry, owned)
            response = client.request(entry['method'], path, headers=who, params=params, json=body)
            passed = response.status_code in (401, 403)
            record(entry, 'forbidden_role:' + role, 'passed' if passed else 'failed', actual=response.status_code, concrete_path=path)
            if not passed: failures.append((role, entry['method'], entry['path'], response.status_code))
    assert not failures, failures


def test_sensitive_dto_types_and_lengths_reject_invalid_bodies(client, owned):
    schema = client.get('/openapi.json').json()
    failures = []; admin = None
    def resolve(value):
        if '$ref' in value:
            return schema['components']['schemas'][value['$ref'].split('/')[-1]]
        return value
    for entry in MATRIX:
        if entry['method'] not in ('POST', 'PUT', 'PATCH') or 'anonymous' in entry['roles']:
            continue
        operation = schema['paths'].get(entry['path'], {}).get(entry['method'].lower(), {})
        body_schema = resolve(operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {}))
        properties = body_schema.get('properties', {})
        if not properties:
            record(entry, 'invalid_type_or_length', 'not_applicable', reason='No typed JSON body; authorization/query cases apply')
            continue
        # Every field has an impossible JSON container type; exact credentials are never logged.
        invalid = {key: [] for key in properties}
        path, params, _ = request_parts(entry, owned)
        if 'delegated' in entry['roles']: who = owned['delegated']
        elif 'customer' in entry['roles']: who = owned['alice']
        else:
            admin = admin or login(client, 'admin')
            who = admin
        response = client.request(entry['method'], path, headers=who, params=params, json=invalid)
        passed = response.status_code == 422
        record(entry, 'invalid_type_or_length', 'passed' if passed else 'failed', actual=response.status_code,
            concrete_path=path, request_field_names=sorted(invalid))
        if not passed: failures.append((entry['method'], entry['path'], response.status_code))
    assert not failures, failures


def test_implicit_owner_collections_do_not_accept_foreign_identity_query(client, owned):
    private = (owned['cid'], owned['approval_id'], owned['ticket_id'], owned['goal_id'], owned['session_id'], owned['message_id'])
    paths = ('/api/customer/profile', '/api/customer/accounts', '/api/customer/beneficiaries', '/api/support/tickets',
        '/api/savings-goals', '/api/conversations', '/api/auth/sessions', '/api/notifications', '/api/dev/outbox')
    for path in paths:
        response = client.get(path, headers=owned['bob'], params={'owner_id': 'alice', 'user_id': 'alice'})
        assert response.status_code == 200, (path, response.status_code)
        text = response.text
        assert all(value not in text for value in private), (path, text[:100])
        if path == '/api/customer/profile': assert response.json()['id'] == 'bob'
        if path == '/api/customer/accounts': assert all(item['owner_id'] == 'bob' for item in response.json()['items'])
        entry = next(e for e in MATRIX if e['method'] == 'GET' and e['path'] == path)
        record(entry, 'implicit_owner_filter', 'passed', actual=response.status_code,
            reason='Foreign owner_id/user_id query cannot expose Alice-owned private resources')


def test_oversized_values_with_otherwise_valid_dto_are_rejected(client, owned):
    probes = [
        ('PATCH', '/api/customer/accounts/' + owned['account_id'], {'nickname': 'x' * 81}, owned['alice'], '/api/customer/accounts/{account_id}'),
        ('POST', '/api/support/tickets', {'subject': 'Valid subject', 'description': 'x' * 5001}, owned['alice'], '/api/support/tickets'),
        ('POST', '/api/support/tickets/' + owned['ticket_id'] + '/messages', {'body': 'x' * 5001}, owned['alice'], '/api/support/tickets/{ticket_id}/messages'),
        ('POST', '/api/agent/runs', {'conversation_id': owned['cid'], 'content': 'x' * 4001}, owned['alice'], '/api/agent/runs'),
        ('POST', '/api/agent/preview', {'answer': 'x' * 24001}, owned['delegated'], '/api/agent/preview'),
        ('POST', '/api/transfers', {'to_account': 'ACC-BOB-001', 'amount_vnd': '1000'}, owned['alice'], '/api/transfers'),
    ]
    for method, path, body, who, template in probes:
        response = client.request(method, path, headers=who, json=body)
        assert response.status_code == 422, (path, response.status_code)
        entry = next(e for e in MATRIX if e['method'] == method and e['path'] == template)
        record(entry, 'oversized_or_strict_type', 'passed', actual=response.status_code, concrete_path=path,
            request_field_names=sorted(body), reason='Other required fields are valid; bound or strict type is violated')


def test_explicit_owned_query_filters_do_not_select_another_users_data(client, owned):
    for path, params in [('/api/agent/runs', {'conversation_id': owned['cid']}),
                         ('/api/agent/approvals', {'conversation_id': owned['cid']}),
                         ('/api/transactions', {'account_id': owned['account_id']})]:
        own = client.get(path, headers=owned['alice'], params=params)
        assert own.status_code == 200
        other = client.get(path, headers=owned['bob'], params=params)
        if path == '/api/agent/approvals':
            assert other.status_code == 200 and other.json()['items'] == []
        else:
            assert other.status_code == 404, (path, other.status_code)
        entry = next(e for e in MATRIX if e['method'] == 'GET' and e['path'] == path)
        record(entry, 'cross_owner_query', 'passed', actual=other.status_code,
            reason='Real owned selector: owner positive 200; foreign owner denied or result set empty', resource_exists=True)
