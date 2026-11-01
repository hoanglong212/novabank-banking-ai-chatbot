"""Start bank + isolated agent using existing dependencies; Ctrl+C stops both."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--agent-port', type=int, default=8093)
    parser.add_argument('--db', type=Path)
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
    agent_env = {k: v for k, v in env.items() if k not in ('JWT_SECRET', 'DB_PATH', 'MFA_ENCRYPTION_KEY', 'FRONTEND_DIST')}
    children = []
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for module, cwd, port, child_env in [('agent_service.main:app', ROOT, args.agent_port, agent_env),
                                             ('app.main:app', ROOT / 'backend', args.port, env)]:
            children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', module, '--host', '127.0.0.1', '--port', str(port)],
                cwd=cwd, env=child_env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        print(f'NovaBank: http://127.0.0.1:{args.port} | isolated agent: {args.agent_port}', flush=True)
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
