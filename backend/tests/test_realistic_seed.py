import importlib.util
from pathlib import Path
import sqlite3
import pytest


def loader():
    path = Path(__file__).resolve().parents[2] / 'scripts/seed_realistic.py'
    spec = importlib.util.spec_from_file_location('realistic_seed', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_realistic_seed_has_fifty_multibank_customers_and_balanced_history(tmp_path):
    from app.database import Database
    from app.ledger import reconcile
    target = tmp_path / 'realistic.sqlite3'
    report = loader().seed(target, seed=17)
    assert report['synthetic'] is True
    assert report['customers'] == 50
    assert len(report['months']) == 6
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0] == 50
        counts = conn.execute("SELECT COUNT(a.id) FROM users u LEFT JOIN accounts a ON a.owner_id=u.id WHERE u.role='customer' GROUP BY u.id").fetchall()
        assert len(counts) == 50 and all(row[0] in (2, 3) for row in counts)
        assert conn.execute("SELECT COUNT(*) FROM users WHERE role='customer' AND name LIKE '%Nguyễn%'").fetchone()[0] > 0
        for role in ('support', 'operations', 'auditor', 'admin'):
            assert conn.execute('SELECT COUNT(*) FROM users WHERE role=?', (role,)).fetchone()[0] >= 3
        for table, minimum in [('transactions', 1500), ('beneficiaries', 100), ('cards', 100), ('bills', 200), ('support_tickets', 100), ('savings', 50)]:
            assert conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] >= minimum
        assert conn.execute("SELECT COUNT(*) FROM bills WHERE status='PAID'").fetchone()[0] == 50
        assert conn.execute("SELECT COUNT(*) FROM bills WHERE status='UNPAID'").fetchone()[0] == 150
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        assert conn.execute('SELECT COUNT(*) FROM accounts WHERE balance_vnd=0').fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM transfers WHERE status='PENDING_OTP'").fetchone()[0] > 0
        assert conn.execute('SELECT MIN(balance_vnd) FROM accounts').fetchone()[0] >= 0
        # A closed reserve with a cancelled deposit has no posted money or journal.
        reserve = conn.execute("""SELECT a.id,a.balance_vnd,t.id,t.direction FROM accounts a
            JOIN transactions t ON t.account_id=a.id
            WHERE a.status='CLOSED' AND t.status='CANCELLED'""").fetchone()
        assert reserve and reserve[1] == 0 and reserve[3] == 'in'
        assert conn.execute('SELECT COUNT(*) FROM ledger_entries WHERE account_id=?', (reserve[0],)).fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM product_transaction_details WHERE transaction_id=?', (reserve[2],)).fetchone()[0] == 0
        from app.identity import digest
        from app.session_security import LOCK_SECONDS, lock_remaining
        disabled = conn.execute("SELECT id FROM users WHERE role='customer' AND status='DISABLED'").fetchone()
        assert disabled and disabled[0] not in ('alice', 'bob', 'charlie')
        lock = conn.execute('SELECT window_start FROM login_lockouts WHERE subject_hash=?', (digest(disabled[0]),)).fetchone()
        assert lock and lock_remaining(conn, disabled[0], lock[0]) == LOCK_SECONDS
    assert reconcile(Database(str(target)))['balanced']


def test_seed_never_overwrites_existing_target_or_report(tmp_path):
    module = loader()
    target = tmp_path / 'existing.sqlite3'
    target.write_bytes(b'preserve original database')
    with pytest.raises(ValueError, match='existing'):
        module.seed(target)
    assert target.read_bytes() == b'preserve original database'
    target = tmp_path / 'new.sqlite3'
    target.with_suffix('.seed.json').write_text('existing report', encoding='utf-8')
    with pytest.raises(ValueError, match='existing'):
        module.seed(target)
    assert not target.exists()
    assert target.with_suffix('.seed.json').read_text(encoding='utf-8') == 'existing report'


def test_fixed_seed_reproduces_business_ids_dates_and_values(tmp_path):
    module = loader()
    first = module.seed(tmp_path / 'one.sqlite3', seed=23)
    second = module.seed(tmp_path / 'two.sqlite3', seed=23)
    assert first['business_fingerprint'] == second['business_fingerprint']
    assert first['counts'] == second['counts']
    assert first['months'] == second['months']
