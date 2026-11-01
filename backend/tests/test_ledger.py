"""Real SQLite migration, immutability and reconciliation contracts."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.database import Database
from app.main import get_db


def report(db):
    from app.ledger import reconcile
    return reconcile(db)


def test_opening_ledger_balances_and_restart_does_not_reseed(client):
    db = get_db()
    with db.connect() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'ledger_accounts', 'ledger_entries', 'reconciliation_runs'} <= tables
        entries = [tuple(row) for row in conn.execute(
            'SELECT journal_id,account_id,amount_vnd FROM ledger_entries ORDER BY journal_id,account_id')]
    assert sum(row[2] for row in entries) == 0
    assert ('OPENING:ACC-ALICE-001', 'ACC-ALICE-001', 12_500_000) in entries
    assert ('OPENING:ACC-BOB-001', 'ACC-BOB-001', 8_750_000) in entries
    db.initialize()
    with db.connect() as conn:
        assert [tuple(row) for row in conn.execute(
            'SELECT journal_id,account_id,amount_vnd FROM ledger_entries ORDER BY journal_id,account_id')] == entries
    result = report(db)
    assert result['balanced'] is True
    assert result['ledger_total_vnd'] == 0
    assert result['mismatches'] == []
    assert result['unbalanced_journals'] == []


def test_legacy_migration_uses_existing_balance_and_preserves_history(tmp_path):
    db = Database(str(tmp_path / 'legacy.sqlite3'))
    with db.connect() as conn:
        conn.execute('CREATE TABLE accounts (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, '
                     'holder_name TEXT NOT NULL, balance_vnd INTEGER NOT NULL CHECK(balance_vnd>=0))')
        conn.execute("INSERT INTO accounts VALUES ('ACC-ALICE-001','alice','ALICE NGUYEN',11234567)")
        conn.execute('CREATE TABLE transactions (id TEXT PRIMARY KEY, account_id TEXT, amount_vnd INTEGER, '
                     'direction TEXT, status TEXT, description TEXT, date TEXT, created_at TEXT)')
        conn.execute("INSERT INTO transactions VALUES ('TX-LEGACY','ACC-ALICE-001',1265433,'out',"
                     "'COMPLETED','Old payment','2026-10-30','2026-10-30T00:00:00+00:00')")
    db.initialize()
    assert db.account('ACC-ALICE-001')['balance_vnd'] == 11_234_567
    assert db.transaction('TX-LEGACY')['description'] == 'Old payment'
    assert report(db)['balanced'] is True
    with db.connect() as conn:
        assert conn.execute("SELECT SUM(amount_vnd) FROM ledger_entries WHERE account_id='ACC-ALICE-001'").fetchone()[0] == 11_234_567
    db.initialize()
    assert db.account('ACC-ALICE-001')['balance_vnd'] == 11_234_567
    assert report(db)['balanced'] is True


@pytest.mark.parametrize('statement', [
    'UPDATE ledger_entries SET amount_vnd=1',
    'DELETE FROM ledger_entries',
    "INSERT OR REPLACE INTO ledger_entries SELECT id,journal_id,account_id,amount_vnd+1,created_at FROM ledger_entries LIMIT 1",
    "UPDATE transactions SET amount_vnd=1 WHERE status='COMPLETED'",
    "DELETE FROM transactions WHERE status='COMPLETED'",
    "INSERT OR REPLACE INTO transactions SELECT id,account_id,amount_vnd+1,direction,status,description,date,created_at FROM transactions WHERE status='COMPLETED' LIMIT 1",
])
def test_posted_history_cannot_be_rewritten(client, statement):
    with pytest.raises(sqlite3.IntegrityError, match='IMMUTABLE'):
        with get_db().connect() as conn:
            conn.execute(statement)


def test_reconciliation_reports_drift_and_restart_does_not_hide_it(client):
    db = get_db()
    with db.connect() as conn:
        conn.execute("UPDATE accounts SET balance_vnd=balance_vnd+123 WHERE id='ACC-ALICE-001'")
    db.initialize()
    result = report(db)
    assert result['balanced'] is False
    assert result['mismatches'] == [{'account_id': 'ACC-ALICE-001', 'balance_vnd': 12_500_123,
                                     'ledger_balance_vnd': 12_500_000}]
    with db.connect() as conn:
        saved = json.loads(conn.execute('SELECT report_json FROM reconciliation_runs WHERE id=?', (result['id'],)).fetchone()[0])
        assert saved == result


def test_unbalanced_journal_is_detected_even_if_total_and_cache_still_match(client):
    db = get_db()
    with db.connect() as conn:
        conn.execute("INSERT INTO ledger_entries VALUES ('bad1','bad-a','SYS-CLEARING',1000,'2026-10-31')")
        conn.execute("INSERT INTO ledger_entries VALUES ('bad2','bad-b','SYS-CLEARING',-1000,'2026-10-31')")
    result = report(db)
    assert result['ledger_total_vnd'] == 0
    assert result['balanced'] is False
    assert {row['journal_id'] for row in result['unbalanced_journals']} == {'bad-a', 'bad-b'}


def test_database_rejects_fractional_cached_money(client):
    with pytest.raises(sqlite3.IntegrityError):
        with get_db().connect() as conn:
            conn.execute("UPDATE accounts SET balance_vnd=1.5 WHERE id='ACC-ALICE-001'")


def test_posting_refuses_a_cache_that_disagrees_with_ledger(client, alice):
    from .test_transfers import draft
    from .test_banking_core import confirm
    t = draft(client, alice).json()
    with get_db().connect() as conn:
        conn.execute("UPDATE accounts SET balance_vnd=balance_vnd+1000 WHERE id='ACC-ALICE-001'")
    response = confirm(client, alice, t)
    assert (response.status_code, response.json()['detail']) == (503, 'LEDGER_MISMATCH')
    with get_db().connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM ledger_entries WHERE journal_id=?', (t['id'],)).fetchone()[0] == 0
    assert get_db().account('ACC-ALICE-001')['balance_vnd'] == 12_501_000
    assert report(get_db())['balanced'] is False


def test_reconciliation_cli_reports_clean_and_drifted_database(client, tmp_path):
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'reconcile.py'
    db = get_db()
    result = subprocess.run([sys.executable, str(script), '--db', db.path], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['balanced'] is True
    with db.connect() as conn:
        conn.execute("UPDATE accounts SET balance_vnd=balance_vnd+7 WHERE id='ACC-BOB-001'")
    result = subprocess.run([sys.executable, str(script), '--db', db.path], capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stdout)['mismatches'][0]['account_id'] == 'ACC-BOB-001'


def test_reconciliation_cli_never_creates_a_missing_database(tmp_path):
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'reconcile.py'
    missing = tmp_path / 'missing' / 'bank.sqlite3'
    result = subprocess.run([sys.executable, str(script), '--db', str(missing)], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'does not exist' in result.stderr.lower()
    assert not missing.parent.exists()
