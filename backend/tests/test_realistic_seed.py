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
