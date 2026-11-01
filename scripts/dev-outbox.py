"""Read local simulated emails. Never serves inbox contents over HTTP."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='Explicit path to the running demo SQLite database')
    parser.add_argument('--id', help='Show one message, including its still-valid development action URL')
    parser.add_argument('--email', help='Filter list by recipient')
    parser.add_argument('--origin', default='http://127.0.0.1:8080', help='Local frontend origin for action URLs')
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    try:
        valid_port = origin.port is None or 1 <= origin.port <= 65535
    except ValueError:
        valid_port = False
    if (origin.scheme != 'http' or origin.hostname not in ('localhost', '127.0.0.1', '::1')
            or origin.username is not None or origin.password is not None or not valid_port
            or origin.path not in ('', '/') or origin.query or origin.fragment):
        parser.error('--origin must be an HTTP loopback origin, e.g. http://localhost:5173')
    path = Path(args.db).resolve()
    if not path.is_file():
        parser.error('Database does not exist; start the application first and check --db.')
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            if args.id:
                row = conn.execute('SELECT * FROM dev_outbox WHERE id=?', (args.id,)).fetchone()
                if row is None:
                    parser.error('Message not found')
                result = dict(row)
                action = result.pop('action_path')
                secret = result.pop('secret_text', None)
                result['code'] = secret if secret and result['expires_at'] > int(time.time()) else None
                result['action_url'] = (args.origin.rstrip('/') + action
                                        if action and result['expires_at'] > int(time.time()) else None)
                result['message'] = result.pop('body', None) or ('Your demo password was changed. Previous sessions have ended.'
                                     if result['kind'] == 'PASSWORD_CHANGED' else
                                     'Open action_url in your local browser. A null URL is expired or already used.')
            else:
                result = [dict(row) for row in conn.execute('''
                    SELECT id,recipient,kind,created_at,expires_at FROM dev_outbox
                    WHERE (? IS NULL OR recipient=?) ORDER BY rowid DESC LIMIT 50''',
                    (args.email, args.email.strip().lower() if args.email else None))]
    except sqlite3.Error:
        parser.error('Cannot read the development inbox. Check the database path and schema migration.')
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
