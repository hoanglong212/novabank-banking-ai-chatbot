"""Re-execute the declared contracts for the exact sample already drawn by the wire verifier."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p/'.git').exists())
rows = json.loads((OUT/'api.json').read_text())['cases']['inventory spot']['observations']
with tempfile.TemporaryDirectory(prefix='nb-final-spot-',ignore_cleanup_errors=True) as temp:
    src = Path(temp)/'src'
    subprocess.run(['git','clone','-q','--shared','--no-checkout',str(ROOT),str(src)],check=True)
    subprocess.run(['git','-C',str(src),'checkout','-q','--detach',OUT.parent.name],check=True)
    raw = Path(temp)/'raw.json'
    env = dict(os.environ, NOVABANK_CONTRACT_RESULTS=str(raw),PYTHONDONTWRITEBYTECODE='1')
    keys = [' '.join((r['service'],r['method'],r['path'])) for r in rows if r['path']!='/openapi.json']
    test = 'backend/tests/test_openapi_contracts.py::test_openapi_operation'
    result = subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
                             *[f'{test}[{k}]' for k in keys]],cwd=src,env=env)
    sys.path[:0] = [str(src),str(src/'backend')]
    from agent_service.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        response=client.head('/openapi.json')
    data = {'source_commit':OUT.parent.name,'pytest_exit':result.returncode,
            'contracts':json.loads(raw.read_text()) if raw.exists() else {},
            'agent_framework_head':{'http':response.status_code,'mime':response.headers.get('content-type'),'bytes':len(response.content)}}
    (OUT/'spot-contracts.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    if (result.returncode or set(data['contracts'])!=set(keys) or response.status_code!=200
            or 'json' not in response.headers.get('content-type','') or response.content):
        raise SystemExit(1)
