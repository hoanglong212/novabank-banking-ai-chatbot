"""Daily encrypted consistent backup; no automatic deletion of archives."""
import importlib.util
import json
import os
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('bank_backup', Path(__file__).with_name('backup.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
while True:
    try:
        output = Path(os.environ.get('BACKUP_DIR', '/backups'))
        result = module.backup(Path(os.environ['DB_PATH']), output, Path(os.environ.get('BACKUP_KEY_FILE', '/run/secrets/backup_key')))
        print(json.dumps({'event': 'backup_completed', **result}), flush=True)
        time.sleep(86400)
    except Exception as exc:
        print(json.dumps({'event': 'backup_failed', 'error_type': type(exc).__name__}), flush=True)
        time.sleep(300)
