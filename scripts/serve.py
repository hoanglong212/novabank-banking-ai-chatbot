"""Start bank + isolated agent using existing dependencies; Ctrl+C stops both."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def lan_addresses():
    try:
        return sorted({a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)} - {'127.0.0.1'})
    except OSError:
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--agent-port', type=int, default=8093)
    parser.add_argument('--db', type=Path)
    # 0.0.0.0 exposes the demo (and its per-user /outbox) to the network: lab use only, e.g. Caido/Burp in a VM.
    parser.add_argument('--host', default=os.environ.get('NOVABANK_HOST', '127.0.0.1'))
    parser.add_argument('--proxy', default=os.environ.get('NOVABANK_UPSTREAM_PROXY', ''),
                        help='Send bank->agent, agent->bank and model traffic through this HTTP proxy (Caido/Burp listener).')
    args = parser.parse_args()
    if args.port == args.agent_port or not all(1024 <= p <= 65535 for p in (args.port, args.agent_port)):
        parser.error('Choose two different unprivileged ports.')
    load_dotenv(ROOT / 'backend' / '.env')
    env = os.environ.copy()
    env.update(FRONTEND_DIST=str(ROOT / 'frontend' / 'dist'),
               BANKING_API_URL=f'http://127.0.0.1:{args.port}', AGENT_SERVICE_URL=f'http://127.0.0.1:{args.agent_port}',
               BANK_REQUIRE_AGENT='true', LEGACY_AGENT_TEST_MODE='false', PYTHONIOENCODING='utf-8')
    if args.db:
        env['DB_PATH'] = str(args.db.resolve())
    if args.proxy:
        # httpx honours these; an empty NO_PROXY makes loopback calls go through the proxy too.
        env.update(HTTP_PROXY=args.proxy, HTTPS_PROXY=args.proxy, NO_PROXY='', no_proxy='')
    agent_env = {k: v for k, v in env.items() if k not in ('JWT_SECRET', 'QR_SIGNING_KEY', 'OTP_HASH_KEY', 'TRANSFER_TOKEN_KEY', 'MFA_ENCRYPTION_KEY', 'DB_PATH', 'FRONTEND_DIST')}
    children = []
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for module, cwd, port, child_env in [('agent_service.main:app', ROOT, args.agent_port, agent_env),
                                             ('app.main:app', ROOT / 'backend', args.port, env)]:
            children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', module, '--host', args.host, '--port', str(port)],
                cwd=cwd, env=child_env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        print(f'NovaBank: http://127.0.0.1:{args.port} | isolated agent: {args.agent_port}', flush=True)
        if args.host != '127.0.0.1':
            for ip in lan_addresses():
                print(f'  network: app http://{ip}:{args.port}  agent API http://{ip}:{args.agent_port}', flush=True)
        if args.proxy:
            print(f'  internal traffic via proxy {args.proxy}', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
        return next((child.returncode for child in children if child.returncode), 1)
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            if child.poll() is None: child.terminate()
        for child in children:
            try: child.wait(timeout=10)
            except subprocess.TimeoutExpired: child.kill(); child.wait()


if __name__ == '__main__':
    raise SystemExit(main())
