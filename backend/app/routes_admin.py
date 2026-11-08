import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from .database import now
from .dependencies import get_db, require_permission
from .identity import transaction
from .identity_schemas import IdentityInput
from . import session_security as security
from .posting import audit
from .ledger import reconcile
from .admin_dashboard import dashboard

router = APIRouter(prefix='/api/admin')
reader = require_permission('admin:audit:read')
writer = require_permission('settings:write')


class Settings(IdentityInput):
    transfer_fee_vnd: int | None = Field(default=None, ge=0, le=100000)
    transfer_limit_vnd: int | None = Field(default=None, ge=1000, le=100000000)
    daily_limit_vnd: int | None = Field(default=None, ge=1000, le=200000000)
    agent_enabled: bool | None = None


class UserState(IdentityInput):
    status: Literal['ACTIVE', 'DISABLED'] | None = None
    kyc_status: Literal['UNVERIFIED', 'VERIFIED', 'REJECTED'] | None = None


class AccountState(IdentityInput):
    status: Literal['ACTIVE', 'FROZEN', 'CLOSED']


@router.get('/overview')
def overview(user=Depends(reader), db=Depends(get_db), days: int = Query(7, ge=7, le=90)):
    if days not in (7, 30, 90):
        raise HTTPException(422, 'Choose 7, 30 or 90 days.')
    with db.connect() as conn:
        conn.execute('BEGIN')
        return {**overview_counts(conn), 'dashboard': dashboard(conn, days)}


def overview_counts(conn):
    counts = {}
    for table in ('users', 'accounts', 'transactions', 'support_tickets'):
        counts[table] = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    counts['failed_transfers'] = conn.execute("SELECT COUNT(*) FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id WHERE t.status='FAILED' OR s.status='FAILED'").fetchone()[0]
    latest = conn.execute('SELECT report_json FROM reconciliation_runs ORDER BY rowid DESC LIMIT 1').fetchone()
    counts['reconciliation'] = json.loads(latest[0]) if latest else None
    return counts


@router.get('/users')
def users(user=Depends(reader), db=Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    with db.connect() as conn:
        rows = conn.execute('''SELECT u.id,u.name,u.email,u.role,u.status,u.created_at,
            COALESCE(p.kyc_status,'UNVERIFIED') AS kyc_status FROM users u LEFT JOIN customer_profiles p ON p.user_id=u.id
            ORDER BY u.id LIMIT ? OFFSET ?''', (limit, offset))
        return {'items': [dict(r) for r in rows], 'total': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0], 'limit': limit, 'offset': offset}


@router.patch('/users/{user_id}')
def update_user(user_id: str, payload: UserState, user=Depends(writer), db=Depends(get_db)):
    with transaction(db) as conn:
        return apply_user_state(conn, user, user_id, payload)


def apply_user_state(conn, user, user_id, payload):
    target = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if not target:
        raise HTTPException(404, 'User not found.')
    if target['role'] != 'customer':
        raise HTTPException(403, 'This console manages customer identities only.')
    if target['status'] == 'PENDING':
        raise HTTPException(409, 'The customer must verify their email before activation.')
    profile = conn.execute('SELECT kyc_status FROM customer_profiles WHERE user_id=?', (user_id,)).fetchone()
    previous = {'status': target['status'], 'kyc_status': profile[0] if profile else 'UNVERIFIED'}
    if payload.status and payload.status != target['status']:
        conn.execute('UPDATE users SET status=?,auth_version=auth_version+1 WHERE id=?', (payload.status, user_id))
        security.revoke_user(conn, user_id, security.timestamp(), 'ADMIN_STATUS_CHANGED')
    if payload.kyc_status:
        conn.execute('INSERT INTO customer_profiles (user_id,kyc_status) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET kyc_status=excluded.kyc_status', (user_id, payload.kyc_status))
    audit(conn, user.id, 'CUSTOMER_UPDATED', user_id,
          json.dumps({'before': previous, 'after': {**previous, **payload.model_dump(exclude_none=True)}}), now())
    return {'message': 'Customer updated. KYC is simulated; no identity verification service was contacted.'}


@router.get('/accounts')
def accounts(user=Depends(reader), db=Depends(get_db)):
    with db.connect() as conn:
        return {'items': [dict(r) for r in conn.execute('SELECT * FROM accounts ORDER BY id LIMIT 1000')]}


@router.patch('/accounts/{account_id}')
def account_state(account_id: str, payload: AccountState, user=Depends(writer), db=Depends(get_db)):
    with transaction(db) as conn:
        return apply_account_state(conn, user, account_id, payload)


def apply_account_state(conn, user, account_id, payload):
    row = conn.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Account not found.')
    if row['status'] == 'CLOSED':
        raise HTTPException(409, 'Closed accounts cannot be reopened.')
    if payload.status == 'CLOSED':
        pending = conn.execute("SELECT 1 FROM interbank_settlements s JOIN transfers t ON t.id=s.transfer_id WHERE t.from_account=? AND s.status='PENDING'", (account_id,)).fetchone()
        savings = conn.execute("SELECT 1 FROM savings WHERE account_id=? AND status='ACTIVE'", (account_id,)).fetchone()
        debt = conn.execute('SELECT 1 FROM cards WHERE account_id=? AND outstanding_vnd>0', (account_id,)).fetchone()
        if row['balance_vnd'] or savings or debt or pending:
            raise HTTPException(409, 'Close active savings and repay debt; account balance must be zero.')
    conn.execute('UPDATE accounts SET status=? WHERE id=?', (payload.status, account_id))
    audit(conn, user.id, 'ACCOUNT_STATUS', account_id, json.dumps({'before': row['status'], 'after': payload.status}), now())
    return {'message': 'Account status updated.'}


@router.get('/settings')
def settings(user=Depends(reader), db=Depends(get_db)):
    with db.connect() as conn:
        return {r['key']: json.loads(r['value_json']) for r in conn.execute('SELECT * FROM bank_settings')}


@router.patch('/settings')
def update_settings(payload: Settings, user=Depends(writer), db=Depends(get_db)):
    with transaction(db) as conn:
        return apply_settings(conn, user, payload)


def apply_settings(conn, user, payload):
    values = {r['key']: json.loads(r['value_json']) for r in conn.execute('SELECT * FROM bank_settings')}
    previous = values.copy()
    values.update(payload.model_dump(exclude_none=True))
    if values['transfer_limit_vnd'] > values['daily_limit_vnd']:
        raise HTTPException(422, 'Daily limit must be at least the per-transfer limit.')
    for key, value in payload.model_dump(exclude_none=True).items():
        conn.execute('UPDATE bank_settings SET value_json=?,updated_at=? WHERE key=?', (json.dumps(value), now(), key))
        audit(conn, user.id, 'SETTING_UPDATED', key, json.dumps({'before': previous[key], 'after': value}), now())
    return values


@router.post('/reconcile')
def run_reconciliation(user=Depends(writer), db=Depends(get_db)):
    return reconcile(db)


@router.get('/audit')
def audit_events(user=Depends(reader), db=Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    with db.connect() as conn:
        return {'items': [dict(r) for r in conn.execute('SELECT * FROM banking_audit ORDER BY created_at DESC,rowid DESC LIMIT ? OFFSET ?', (limit, offset))],
                'total': conn.execute('SELECT COUNT(*) FROM banking_audit').fetchone()[0], 'offset': offset, 'limit': limit}


class GatewaySwitch(IdentityInput):
    enabled: bool


@router.get('/agent-gateway')
def agent_gateway_status(user=Depends(reader), db=Depends(get_db)):
    from . import agent_gateway
    with db.connect() as conn:
        return {'gateway': agent_gateway.state(conn), 'lab': agent_gateway.lab(), 'metrics': agent_gateway.metrics(conn),
                'log_file': str(agent_gateway.log_path() or '')}


@router.put('/agent-gateway')
def switch_agent_gateway(payload: GatewaySwitch, user=Depends(writer), db=Depends(get_db)):
    from . import agent_gateway
    with transaction(db) as conn:
        return {'gateway': agent_gateway.set_state(conn, user, payload.enabled)}


@router.get('/agent-gateway/log')
def agent_gateway_log(user=Depends(reader), db=Depends(get_db), gateway: Literal['on', 'off'] | None = None,
                      decision: Literal['ALLOW', 'DENY', 'ERROR'] | None = None,
                      offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    from . import agent_gateway
    with db.connect() as conn:
        return agent_gateway.entries(conn, gateway, decision, limit, offset)


@router.get('/agent-gateway/log.csv')
def agent_gateway_log_csv(user=Depends(reader), db=Depends(get_db), gateway: Literal['on', 'off'] | None = None):
    from fastapi.responses import Response
    from . import agent_gateway
    with db.connect() as conn:
        return Response(agent_gateway.csv_text(conn, gateway), media_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="agent-gateway-log.csv"'})
