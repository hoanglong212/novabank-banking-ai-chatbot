"""Verify migration on SQLite backup copies, including row preservation and originals."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.database import Database
from app.ledger import reconcile


def rows(conn):
    data = {}
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        names = [r[1] for r in conn.execute('PRAGMA table_info("' + table + '")')]
        records = conn.execute('SELECT * FROM "' + table + '"').fetchall()
        data[table] = (names, set(tuple(r) for r in records))
    return data


def main():
    parent = ROOT / '.local' / 'full-roadmap'; parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='migration-', dir=parent)); checks = []
    for i, source in enumerate([ROOT / 'novabank_demo.sqlite3', ROOT / 'backend' / 'novabank_demo.sqlite3']):
        if not source.is_file(): continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest(); copy = output / f'copy-{i}.sqlite3'
        with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as conn, sqlite3.connect(copy) as target:
            before = rows(conn); conn.backup(target)
        db = Database(str(copy)); db.initialize()
        with db.connect() as conn:
            preserved = {}
            for table, (columns, old) in before.items():
                projection = ','.join('"' + column + '"' for column in columns)
                new = set(tuple(r) for r in conn.execute('SELECT ' + projection + ' FROM "' + table + '"'))
                preserved[table] = old <= new
            versions = [r[0] for r in conn.execute('SELECT version FROM schema_migrations ORDER BY version')]
            integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
        check = {'source': str(source.relative_to(ROOT)), 'original_unchanged': hashlib.sha256(source.read_bytes()).hexdigest() == digest,
                 'old_rows_preserved': all(preserved.values()), 'tables': preserved, 'versions': versions,
                 'integrity': integrity, 'ledger_balanced': reconcile(db)['balanced']}
        checks.append(check)
    result = {'checks': checks, 'passed': bool(checks) and all(c['original_unchanged'] and c['old_rows_preserved'] and c['ledger_balanced'] and c['integrity']=='ok' for c in checks)}
    (parent / 'migration-final.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2)); return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
