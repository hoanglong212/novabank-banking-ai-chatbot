import importlib.util
import json
from pathlib import Path
import pytest
from tests.acceptance_helpers import client, get_db  # noqa: F401

def helper():
    path=Path(__file__).resolve().parents[2]/'scripts/check-document-seed.py'
    spec=importlib.util.spec_from_file_location('check_document_seed',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_consistency_and_fixture_cleanup_requires_synthetic_manifest(client):
    db=get_db()
    with db.connect() as conn:
        path=Path(conn.execute('PRAGMA database_list').fetchone()[2])
        conn.execute("INSERT INTO transactions VALUES ('TX-PENTEST-E1','ACC-ALICE-001',1000,'in','COMPLETED','Synthetic display fixture','2026-11-18','2026-11-18T00:00:00+00:00')")
    assert helper().check(path)['pentest_fixture_rows']==1
    with pytest.raises(ValueError,match='manifest'):
        helper().check(path,True)
    path.with_suffix('.seed.json').write_text(json.dumps({'synthetic':True}),encoding='utf-8')
    result=helper().check(path,True)
    assert result['balanced'] and result['pentest_fixture_rows']==0

    with db.connect() as conn:
        with pytest.raises(Exception,match="IMMUTABLE"):
            conn.execute("DELETE FROM transactions WHERE status='COMPLETED'")
