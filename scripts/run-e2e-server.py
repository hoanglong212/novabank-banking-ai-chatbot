"""Disposable browser-test server; never reads or resets the working demo database."""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

def test_disposable_bank_server():
    """Keep legacy compatibility cases inside a real pytest test process."""
    output = ROOT / '.local' / 'e2e'
    output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='run-', dir=output))
    db_path = run / 'acceptance.sqlite3'
    os.environ.update(ENV='demo', DB_PATH=str(db_path), FRONTEND_DIST=str(ROOT / 'frontend' / 'dist'),
                      LLM_PROVIDER='mock', GATEWAY_MODE='local', JWT_SECRET=secrets.token_urlsafe(48), LEGACY_AGENT_TEST_MODE='true')
    # Use the 10m fixture BEFORE migrations derive the opening ledger.
    from app import database
    database.SEED_ACCOUNTS = [(a, owner, name, 10_000_000 if owner == 'alice' else balance)
                              for a, owner, name, balance in database.SEED_ACCOUNTS]
    fixture_db = database.Database(str(db_path))
    fixture_db.initialize()
    from tests.stepup_helpers import fixed_known_payees
    with fixture_db.connect() as conn:
        fixed_known_payees(conn)
    (output / 'latest.json').write_text(json.dumps({'db_path': str(db_path)}), encoding='utf-8')
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=int(os.environ.get('E2E_PORT', '8092')), log_level='warning')

if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main(['-q', '-s', __file__]))
