"""Runtime logging probe against a real uvicorn subprocess and disposable DB."""
from tests.acceptance_helpers import ROOT
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import httpx


def test_SEC_09_runtime_logs_never_contain_credentials_or_recovery_urls(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    db=tmp_path/'runtime.sqlite3'; logfile=tmp_path/'runtime.log'
    env={**os.environ,'DB_PATH':str(db),'LLM_PROVIDER':'mock','BANK_WORKER_ENABLED':'false','JWT_SECRET':secrets.token_urlsafe(48),'PYTHONIOENCODING':'utf-8'}
    with logfile.open('w',encoding='utf-8') as output:
        process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT/'backend',env=env,stdout=output,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        canaries={}
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=5) as client:
                for _ in range(120):
                    try:
                        if client.get('/api/health').status_code==200:break
                    except httpx.ConnectError:pass
                    time.sleep(.05)
                else: raise AssertionError('Isolated runtime did not start')
                pending=client.post('/api/auth/login',json={'username':'alice','password':'Alice@2026'})
                assert pending.status_code==202
                with sqlite3.connect(db) as conn:
                    otp=conn.execute("SELECT secret_text FROM dev_outbox WHERE kind='LOGIN_OTP' ORDER BY rowid DESC LIMIT 1").fetchone()[0]
                response=client.post('/api/auth/mfa/verify',json={'challenge_id':pending.json()['challenge_id'],'code':otp})
                assert response.status_code==200
                token=response.json()['access_token']
                canaries={'password':'Alice@2026','OTP':otp,'JWT':token,'refresh':response.json()['refresh_token']}
                for path in ('forgot-password','resend-verification'):
                    assert client.post('/api/auth/'+path,json={'email':'alice@novabank.test'}).status_code==202
                with sqlite3.connect(db) as conn:
                    for kind,secret in conn.execute('SELECT kind,secret_text FROM dev_outbox'):
                        canaries[kind]=secret
                # A caller may accidentally paste a reset URL/query; access logging must not retain it.
                reset='SEC09-reset-token-'+secrets.token_hex(12)
                verify='SEC09-verify-token-'+secrets.token_hex(12)
                canaries.update(reset=reset,verify=verify)
                client.get('/reset-password?token='+reset,headers={'Authorization':'Bearer '+token})
                client.get('/verify-email?token='+verify)
        finally:
            process.terminate();process.wait(timeout=10)
    raw=logfile.read_text(encoding='utf-8')
    assert 'http_request' in raw and 'POST' in raw
    leaked=[label for label,value in canaries.items() if value and value in raw]
    assert not leaked, 'Sensitive runtime log fields: '+', '.join(leaked)
