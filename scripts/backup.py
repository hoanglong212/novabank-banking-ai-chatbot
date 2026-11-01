"""Encrypted SQLite snapshot/restore, including the per-database MFA encryption key.

Never replaces an existing restore target. Keep the backup key separate from archives.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import zipfile
from cryptography.fernet import Fernet


def make_key(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(Fernet.generate_key())
    path.chmod(0o600)


def backup(db, out, key_file):
    db = db.resolve()
    if not db.is_file():
        raise ValueError('Source database does not exist')
    cipher = Fernet(key_file.read_bytes().strip())
    with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(':memory:') as snapshot:
        source.backup(snapshot)
        if snapshot.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Source database integrity check failed')
        data = snapshot.serialize()
    items = {'bank.sqlite3': data}
    mfa = Path(str(db) + '.mfa.key')
    if mfa.exists():
        items['bank.mfa.key'] = mfa.read_bytes()
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(),
                'sha256': {name: hashlib.sha256(value).hexdigest() for name, value in items.items()}}
    payload = BytesIO()
    with zipfile.ZipFile(payload, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in items.items():
            archive.writestr(name, value)
        archive.writestr('manifest.json', json.dumps(manifest))
    out.mkdir(parents=True, exist_ok=True)
    target = out / ('NovaBank-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.backup')
    with target.open('xb') as output:
        output.write(cipher.encrypt(payload.getvalue()))
    return {'archive': str(target), **manifest}


def restore(archive, db, key_file):
    key_target = Path(str(db) + '.mfa.key')
    if db.exists() or key_target.exists():
        raise ValueError('Restore target or its MFA key already exists; choose a new path')
    plain = Fernet(key_file.read_bytes().strip()).decrypt(archive.read_bytes())
    with zipfile.ZipFile(BytesIO(plain)) as source:
        manifest = json.loads(source.read('manifest.json'))
        items = {name: source.read(name) for name in manifest['sha256'] if name in ('bank.sqlite3', 'bank.mfa.key')}
    if 'bank.sqlite3' not in items or any(hashlib.sha256(value).hexdigest() != manifest['sha256'][name] for name, value in items.items()):
        raise ValueError('Backup checksum validation failed')
    with sqlite3.connect(':memory:') as check:
        check.deserialize(items['bank.sqlite3'])
        if check.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Backup database integrity check failed')
    db.parent.mkdir(parents=True, exist_ok=True)
    with db.open('xb') as output:
        output.write(items['bank.sqlite3'])
    if 'bank.mfa.key' in items:
        with key_target.open('xb') as output:
            output.write(items['bank.mfa.key'])
        key_target.chmod(0o600)
    return {'restored_db': str(db), 'mfa_key_restored': 'bank.mfa.key' in items, 'source_created_at': manifest['created_at']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['keygen', 'backup', 'restore'])
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--db', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    if args.command == 'keygen':
        make_key(args.key_file); result = {'message': 'Backup key created; protect it separately from the archives.'}
    elif args.command == 'backup':
        if not args.db or not args.out: parser.error('backup requires --db and --out')
        result = backup(args.db, args.out, args.key_file)
    else:
        if not args.db or not args.archive: parser.error('restore requires --db and --archive')
        result = restore(args.archive, args.db, args.key_file)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
