"""Run updated acceptance against an isolated temporary DB/server, then stop it."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0))
    port = probe.getsockname()[1]
base = f'http://127.0.0.1:{port}'
with tempfile.TemporaryDirectory(prefix='novabank-auth-live-') as temporary:
    env = {**os.environ, 'DB_PATH':str(Path(temporary)/'demo.sqlite3'), 'APP_ORIGINS':base,
           'AUTH_COOKIE_SECURE':'false','LLM_PROVIDER':'mock','GATEWAY_MODE':'local',
           'FRONTEND_DIST':str(ROOT/'frontend/dist')}
    log = ROOT/'docs/day1-followup-2026-10-23/auth-live-server.log'
    with log.open('w',encoding='utf-8') as output:
        process = subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                                   cwd=ROOT/'backend',env=env,stdout=output,stderr=output,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError('Isolated server exited; inspect auth-live-server.log')
                try:
                    if httpx.get(base+'/api/health',timeout=1).status_code==200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError('Isolated server did not become ready')
            subprocess.run([sys.executable,str(ROOT/'scripts/check-demo.py'),base,'mock'],cwd=ROOT,check=True)
        finally:
            process.terminate()
            process.wait(timeout=15)
print('PASS: isolated server stopped and SQLite directory removed')
