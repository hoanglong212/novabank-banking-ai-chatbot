"""Actual two-process / local-model acceptance; all banking data is disposable."""
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def main():
    directory = ROOT / '.local' / 'full-roadmap'; directory.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='agent-check-', dir=directory))
    bank_port, agent_port = port(), port()
    bank_url, agent_url = f'http://127.0.0.1:{bank_port}', f'http://127.0.0.1:{agent_port}'
    db = output / 'bank.sqlite3'
    env = os.environ.copy(); env.update(DB_PATH=str(db), JWT_SECRET=secrets.token_urlsafe(48),
        LLM_PROVIDER='ollama', OLLAMA_MODEL='qwen2.5:7b', BANK_WORKER_ENABLED='false',
        AGENT_SERVICE_URL=agent_url, BANKING_API_URL=bank_url, PYTHONIOENCODING='utf-8')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    children, logs = [], []
    report = {'output': str(output), 'checks': []}
    try:
        for name, module, cwd, number in [('bank', 'app.main:app', ROOT / 'backend', bank_port), ('agent', 'agent_service.main:app', ROOT, agent_port)]:
            local_env = env.copy()
            if name == 'agent':
                for key in ('DB_PATH', 'JWT_SECRET', 'QR_SIGNING_KEY', 'OTP_HASH_KEY', 'TRANSFER_TOKEN_KEY', 'MFA_ENCRYPTION_KEY'):
                    local_env.pop(key, None)
            log = (output / (name + '.log')).open('w', encoding='utf-8'); logs.append(log)
            children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', module, '--host', '127.0.0.1', '--port', str(number)],
                cwd=cwd, env=local_env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags))
        with httpx.Client(base_url=bank_url, timeout=180) as client:
            for _ in range(100):
                try:
                    if client.get('/api/health').status_code == 200 and httpx.get(agent_url + '/health').status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError('Test services did not start')
            def login(name):
                challenge = client.post('/api/auth/login', json={'username': name, 'password': name.capitalize() + '@2026'}).json()['challenge_id']
                import hashlib
                with sqlite3.connect(db) as conn:
                    code = conn.execute('SELECT secret_text FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1', (hashlib.sha256(challenge.encode()).hexdigest(),)).fetchone()[0]
                response = client.post('/api/auth/mfa/verify', json={'challenge_id': challenge, 'code': code}); response.raise_for_status()
                return {'Authorization': 'Bearer ' + response.json()['access_token']}
            admin = login('admin')
            indexed = client.post('/api/admin/knowledge-index', headers=admin); indexed.raise_for_status()
            report['index'] = indexed.json(); print('Indexed', indexed.json(), flush=True)
            alice = login('alice')
            for prompt, expected in [('What is my account balance?', 'get_account_balance'),
                                     ('What interest rate does NovaBank offer for 6 month savings?', 'search_knowledge'),
                                     ('Transfer 200000 VND to ACC-BOB-001 content lunch', 'prepare_transfer')]:
                cid = client.post('/api/conversations', headers=alice, json={'title': 'Agent service acceptance'}).json()['id']
                started = time.perf_counter()
                response = client.post(f'/api/conversations/{cid}/stream', headers=alice, json={'content': prompt, 'profile': 'defended'})
                response.raise_for_status()
                frames = []
                for frame in response.text.split('\n\n'):
                    lines = frame.splitlines(); name = next((x[7:] for x in lines if x.startswith('event: ')), '')
                    data = next((x[6:] for x in lines if x.startswith('data: ')), None)
                    if data:
                        frames.append({'event': name, 'data': json.loads(data)})
                run = next(x['data']['run_id'] for x in frames if x['event'] == 'run')
                trace = client.get('/api/agent/runs/' + run, headers=alice).json()
                checks = {'prompt': prompt, 'latency_seconds': round(time.perf_counter()-started, 2), 'trace': trace,
                          'events': [x['event'] for x in frames], 'expected_tool': expected,
                          'passed': trace['status'] == 'COMPLETED' and any(c['name'] == expected and c['decision'] == 'ALLOW' for c in trace['tool_calls'])}
                report['checks'].append(checks)
                checks['text_frames'] = sum(x['event'] == 'text' for x in frames)
                if expected == 'search_knowledge':
                    checks['inline_citation'] = '[KB-' in (trace.get('answer') or '')
                    checks['passed'] = checks['passed'] and checks['inline_citation'] and checks['text_frames'] > 0
                print(prompt, '=>', trace['status'], checks['passed'], checks['latency_seconds'], flush=True)
            cid = client.post('/api/conversations', headers=alice, json={'title':'Cancellation acceptance'}).json()['id']
            with client.stream('POST', f'/api/conversations/{cid}/stream', headers=alice, json={'content':'Explain savings and transfer fees in detail.','profile':'defended'}) as stream:
                stream.raise_for_status()
                for line in stream.iter_lines():
                    if line.startswith('data: '):
                        run_id = json.loads(line[6:])['run_id']
                        cancelled = client.post('/api/agent/runs/'+run_id+'/cancel', headers=alice)
                        cancelled.raise_for_status()
                        report['cancelled'] = cancelled.json()['status'] == 'CANCELLED'
                        break
            with sqlite3.connect(db) as conn:
                report['money_unchanged'] = conn.execute("SELECT balance_vnd FROM accounts WHERE id='ACC-ALICE-001'").fetchone()[0] == 12500000
                report['approval_count'] = conn.execute("SELECT COUNT(*) FROM tool_approvals WHERE status='PENDING'").fetchone()[0]
        report['passed'] = all(c['passed'] for c in report['checks']) and report['money_unchanged'] and report['approval_count'] > 0 and report.get('cancelled')
    finally:
        for child in children:
            child.terminate()
        for child in children:
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
        for log in logs: log.close()
        (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        (directory / 'latest-agent-check.json').write_text(json.dumps({'report': str(output / 'report.json')}), encoding='utf-8')
    print('Report:', output / 'report.json', flush=True)
    return 0 if report.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
