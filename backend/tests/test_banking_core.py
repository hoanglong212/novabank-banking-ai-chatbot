"""Money invariants through real API calls and independent SQLite connections."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app import transfers, vietqr
from app.auth import USERS
from app.database import Database
from app.main import get_db
from .test_guard_qr_langgraph import BANKS
from .test_transfers import balance, draft
from .test_ledger import report


@pytest.fixture(autouse=True)
def financial_invariants(client, monkeypatch):
    monkeypatch.setattr(vietqr, '_banks', BANKS)
    yield
    assert report(get_db())['balanced'] is True


def confirm(client, headers, transfer, key=None, otp=None):
    return client.post(f'/api/transfers/{transfer["id"]}/confirm',
                       headers={**headers, **({'Idempotency-Key': key} if key is not None else {})},
                       json={'otp': otp or transfer_code(transfer)})


def test_internal_posting_has_balanced_journal_and_one_audit(client, alice, bob):
    t = draft(client, alice).json()
    assert confirm(client, alice, t, 'internal-1').status_code == 200
    with get_db().connect() as conn:
        rows = [tuple(row) for row in conn.execute(
            'SELECT account_id,amount_vnd FROM ledger_entries WHERE journal_id=? ORDER BY account_id', (t['id'],))]
        assert rows == [('ACC-ALICE-001', -200_000), ('ACC-BOB-001', 200_000)]
        audit = conn.execute("SELECT * FROM banking_audit WHERE action='TRANSFER_COMPLETED' AND resource_id=?", (t['id'],)).fetchall()
        assert len(audit) == 1
        assert (audit[0]['before_balance_vnd'], audit[0]['after_balance_vnd']) == (12_500_000, 12_300_000)
    assert balance(client, bob) == 8_950_000


def test_interbank_has_clearing_counterentry(client, alice):
    t = draft(client, alice, to_bank='VCB', to_account='0123456789').json()
    assert confirm(client, alice, t).status_code == 200
    with get_db().connect() as conn:
        assert conn.execute("SELECT amount_vnd FROM ledger_entries WHERE journal_id=? AND account_id='SYS-CLEARING'",
                            (t['id'],)).fetchone()[0] == 200_000


def test_idempotent_replay_returns_original_receipt_after_balance_changes(client, alice):
    t = draft(client, alice).json()
    first = confirm(client, alice, t, 'payment-1')
    assert first.status_code == 200
    assert confirm(client, alice, draft(client, alice).json(), 'payment-2').status_code == 200
    replay = confirm(client, alice, t, 'payment-1')
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert replay.json()['balance_vnd'] == 12_300_000
    assert balance(client, alice) == 12_100_000
    with get_db().connect() as conn:
        stored = json.loads(conn.execute("SELECT response_json FROM idempotency_keys WHERE key='payment-1'").fetchone()[0])
        assert 'demo_otp' not in stored and 'otp' not in stored and 'otp_hash' not in stored


def test_idempotency_conflict_does_not_touch_second_draft(client, alice):
    first, second = draft(client, alice).json(), draft(client, alice).json()
    assert confirm(client, alice, first, 'same-key').status_code == 200
    conflict = confirm(client, alice, second, 'same-key')
    assert (conflict.status_code, conflict.json()['detail']) == (409, 'IDEMPOTENCY_CONFLICT')
    assert get_db().get_transfer(second['id'], 'alice')['status'] == 'PENDING_OTP'
    assert confirm(client, alice, second, 'another-key').status_code == 200


def test_idempotency_is_scoped_to_authenticated_user(client, alice, bob):
    a = draft(client, alice).json()
    assert confirm(client, alice, a, 'common-key').status_code == 200
    assert confirm(client, bob, a, 'common-key').status_code == 404
    b = draft(client, bob, to_account='ACC-ALICE-001').json()
    assert confirm(client, bob, b, 'common-key').status_code == 200
    assert balance(client, alice) == 12_500_000


def test_wrong_otp_does_not_consume_idempotency_key(client, alice):
    t = draft(client, alice).json()
    wrong = '000000' if transfer_code(t) != '000000' else '111111'
    assert confirm(client, alice, t, 'retry-key', wrong).json()['detail'] == 'OTP_INVALID'
    assert confirm(client, alice, t, 'retry-key').status_code == 200
    assert confirm(client, alice, t, 'retry-key').status_code == 200


@pytest.mark.parametrize('value', [1000.0, 1000.5, '200000', True, 0, -1000, 100_000_001])
def test_transfer_requires_integer_vnd_in_range(client, alice, value):
    assert draft(client, alice, amount_vnd=value).status_code == 422


@pytest.mark.parametrize('key', ['', ' ', 'x' * 129])
def test_invalid_idempotency_key_never_posts(client, alice, key):
    t = draft(client, alice).json()
    assert confirm(client, alice, t, key).status_code == 422
    assert balance(client, alice) == 12_500_000


@pytest.mark.parametrize('account', ['ACC-ALICE-001', 'ACC-BOB-001'])
@pytest.mark.parametrize('status', ['FROZEN', 'CLOSED'])
def test_account_state_checked_during_prepare_and_confirm(client, alice, account, status):
    t = draft(client, alice).json()
    with get_db().connect() as conn:
        conn.execute('UPDATE accounts SET status=? WHERE id=?', (status, account))
    assert draft(client, alice).json()['detail'] == 'ACCOUNT_NOT_ACTIVE'
    assert confirm(client, alice, t).json()['detail'] == 'ACCOUNT_NOT_ACTIVE'
    assert balance(client, alice) == 12_500_000


def test_expired_quote_cannot_be_revived_by_otp_resend(client, alice, monkeypatch):
    monkeypatch.setattr(transfers, 'now', lambda: '2026-10-31T10:00:00+00:00')
    t = draft(client, alice).json()
    assert t['expires_at'] == '2026-10-31T10:05:00+00:00'
    transfer_code(t)  # Read the delivered code before expiry invalidates the mailbox secret.
    monkeypatch.setattr(transfers, 'now', lambda: '2026-10-31T10:05:00+00:00')
    assert client.post(f'/api/transfers/{t["id"]}/otp', headers=alice).json()['detail'] == 'DRAFT_EXPIRED'
    # The B5 token expires with the draft, so it may refuse first.
    assert confirm(client, alice, t).json()['detail'] in ('DRAFT_EXPIRED', 'ALREADY_PROCESSED', 'TOKEN_EXPIRED')
    assert balance(client, alice) == 12_500_000


def test_otp_expiry_boundary_and_action_binding(client, alice, monkeypatch):
    monkeypatch.setattr(transfers, 'now', lambda: '2026-10-31T10:00:00+00:00')
    # Deterministic distinct OTPs test that a valid OTP from another transfer is rejected.
    numbers = iter([123456, 654321])
    monkeypatch.setattr(transfers.secrets, 'randbelow', lambda _: next(numbers))
    a, b = draft(client, alice).json(), draft(client, alice).json()
    assert confirm(client, alice, b, otp=transfer_code(a)).json()['detail'] == 'OTP_INVALID'
    monkeypatch.setattr(transfers, 'now', lambda: '2026-10-31T10:02:00+00:00')
    assert confirm(client, alice, a).json()['detail'] == 'OTP_EXPIRED'


def test_rollback_after_debit_leaves_no_financial_effect(client, alice, bob):
    t = draft(client, alice).json()
    with get_db().connect() as conn:
        conn.execute("""CREATE TRIGGER fail_credit BEFORE INSERT ON ledger_entries
                        WHEN NEW.journal_id LIKE 'TRF-%' AND NEW.amount_vnd>0
                        BEGIN SELECT RAISE(ABORT,'injected credit failure'); END""")
    response = confirm(client, alice, t, 'failed-payment')
    assert (response.status_code, response.json()['detail']) == (503, 'POSTING_FAILED')
    assert (balance(client, alice), balance(client, bob)) == (12_500_000, 8_750_000)
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM ledger_entries WHERE journal_id=?', (t['id'],)).fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0] == 7
        assert conn.execute('SELECT COUNT(*) FROM idempotency_keys').fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM banking_audit WHERE action='TRANSFER_COMPLETED'").fetchone()[0] == 0
    assert get_db().get_transfer(t['id'], 'alice')['failure_reason'] == 'POSTING_FAILED'


def token(t):
    # HTTP drafts carry their B5 token; drafts made with transfers.prepare() get one exactly as the route issues it.
    from app.transfer_token import issue
    return t.get('confirm_token') or issue(t, transfers._expires_at(t), transfers.now())


def simultaneous_confirm(db, drafts, keys, otps=None):
    barrier = Barrier(len(drafts))
    def run(item):
        index, t = item
        barrier.wait(timeout=5)
        try:
            return transfers.confirm(db, USERS['alice'], t['id'], (otps or [transfer_code(d) for d in drafts])[index], keys[index], token(t))
        except transfers.TransferError as exc:
            return exc.reason_code
    with ThreadPoolExecutor(max_workers=len(drafts)) as pool:
        return list(pool.map(run, enumerate(drafts)))


def test_concurrent_same_key_confirms_post_once(client, alice):
    t = draft(client, alice).json()
    results = simultaneous_confirm(get_db(), [t, t], ['simultaneous', 'simultaneous'])
    assert isinstance(results[0], dict) and results[0] == results[1]
    assert balance(client, alice) == 12_300_000
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM ledger_entries WHERE journal_id=?', (t['id'],)).fetchone()[0] == 2


def test_concurrent_wrong_otps_share_three_attempt_budget(client, alice):
    t = draft(client, alice).json()
    wrong = '000000' if transfer_code(t) != '000000' else '111111'
    results = simultaneous_confirm(get_db(), [t] * 5, ['wrong'] * 5, [wrong] * 5)
    assert sorted(results) == ['ALREADY_PROCESSED', 'ALREADY_PROCESSED', 'OTP_INVALID', 'OTP_INVALID', 'OTP_LOCKED']
    assert get_db().get_transfer(t['id'], 'alice')['otp_attempts'] == 3


def test_two_six_million_transfers_from_ten_million_only_one_succeeds(tmp_path):
    db = Database(str(tmp_path / 'concurrency.sqlite3'))
    with db.connect() as conn:
        conn.execute('CREATE TABLE accounts (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, '
                     'holder_name TEXT NOT NULL, balance_vnd INTEGER NOT NULL CHECK(balance_vnd>=0))')
        conn.execute("INSERT INTO accounts VALUES ('ACC-ALICE-001','alice','ALICE NGUYEN',10000000)")
    db.initialize()
    drafts = []
    for _ in range(2):
        t = asyncio.run(transfers.prepare(db, USERS['alice'], {
            'to_bank': 'NovaBank', 'to_account': 'ACC-BOB-001', 'amount_vnd': 6_000_000}))
        _, otp = transfers.issue_otp(db, USERS['alice'], t['id'])
        drafts.append({**t, 'demo_otp': otp})
    results = simultaneous_confirm(db, drafts, ['six-a', 'six-b'])
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 'INSUFFICIENT_FUNDS' in results
    assert db.account('ACC-ALICE-001')['balance_vnd'] == 4_000_000
    assert db.account('ACC-BOB-001')['balance_vnd'] == 14_750_000
    assert report(db)['balanced'] is True


def test_daily_limit_rechecked_at_confirm_using_vietnam_day(client, alice, monkeypatch):
    monkeypatch.setattr(transfers, 'DAILY_LIMIT_VND', 300_000)
    # Both UTC dates belong to 1 November in Vietnam.
    monkeypatch.setattr(transfers, 'now', lambda: '2026-10-31T23:59:00+00:00')
    first, second = draft(client, alice).json(), draft(client, alice).json()
    assert confirm(client, alice, first).status_code == 200
    monkeypatch.setattr(transfers, 'now', lambda: '2026-11-01T00:00:00+00:00')
    assert confirm(client, alice, second).json()['detail'] == 'DAILY_LIMIT_EXCEEDED'
    assert draft(client, alice).json()['detail'] == 'DAILY_LIMIT_EXCEEDED'
    monkeypatch.setattr(transfers, 'now', lambda: '2026-11-01T17:00:00+00:00')
    assert confirm(client, alice, draft(client, alice).json()).status_code == 200


def test_cors_accepts_idempotency_header(client):
    response = client.options('/api/transfers/example/confirm', headers={
        'Origin': 'http://127.0.0.1:5173', 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type,idempotency-key'})
    assert response.status_code == 200

from tests.conftest import transfer_code
