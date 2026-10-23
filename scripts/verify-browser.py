"""Start isolated backend + Vite for the existing Edge CDP identity test."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]
backend_port, frontend_port = free_port(), free_port()
base = f'http://127.0.0.1:{frontend_port}'
httpx.get('http://127.0.0.1:9224/json/list', timeout=3).raise_for_status()
node = shutil.which('node')
if not node:
    raise SystemExit('Node is required')
processes = []
with tempfile.TemporaryDirectory(prefix='novabank-browser-') as temporary:
    env = {**os.environ,'DB_PATH':str(Path(temporary)/'browser.sqlite3'),
           'APP_ORIGINS':base,'AUTH_COOKIE_SECURE':'false',
           'NOVABANK_TEST_URL':base,'NOVABANK_API_TARGET':f'http://127.0.0.1:{backend_port}',
           'LLM_PROVIDER':'mock','GATEWAY_MODE':'local'}
    logdir = ROOT/'docs/day2-evidence-2026-10-23'
    logdir.mkdir(parents=True,exist_ok=True)
    with (logdir/'servers.log').open('w',encoding='utf-8') as log:
        try:
            for argv,cwd in [
                ([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(backend_port)],ROOT/'backend'),
                ([node,str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',str(frontend_port),'--strictPort'],ROOT/'frontend'),
            ]:
                processes.append(subprocess.Popen(argv,cwd=cwd,env=env,stdout=log,stderr=log,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
            for _ in range(100):
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError('Test server exited; inspect servers.log')
                try:
                    if httpx.get(base+'/api/health',timeout=1).status_code==200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError('Timed out waiting for same-origin UI/API')
            subprocess.run([node,'scripts/check-user-switch.mjs'],cwd=ROOT/'frontend',env=env,check=True,timeout=120)
        finally:
            for process in reversed(processes):
                process.terminate()
                process.wait(timeout=15)
print('PASS: test servers stopped; temporary database removed')
