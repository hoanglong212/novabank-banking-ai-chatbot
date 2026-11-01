"""Check an existing NovaBank ledger and save a report; never initialize or reset a DB."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path, help='Path to an existing, migrated SQLite database')
    args = parser.parse_args()
    path = args.db.resolve()
    if not path.is_file():
        print('Database does not exist; no file was created.', file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    from app.database import Database
    from app.ledger import reconcile
    try:
        result = reconcile(Database(str(path)))
    except (sqlite3.Error, ValueError):
        print('Cannot reconcile this database. Check its schema and access; start the updated app once to migrate it.',
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['balanced'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
