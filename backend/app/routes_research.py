"""Read-only experiment evidence and an explicit admin-triggered sandbox runner."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import Field
from .config import setting
from .dependencies import current_user, require_permission
from .identity_schemas import IdentityInput

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / '.local' / 'research'
def research_access(user=Depends(current_user)):
    if user.role != 'admin' or setting('RESEARCH_SANDBOX_ENABLED', 'false').lower() != 'true':
        raise HTTPException(403, 'Research requires an administrator and an enabled sandbox.')
    return user


router = APIRouter(prefix='/api/research', dependencies=[Depends(research_access)])
_process = None


def run_directory(run_id):
    if not re.fullmatch(r'run-\d{8}-\d{6}-[0-9a-f]{6}', run_id):
        raise HTTPException(404, 'Experiment not found.')
    path = (REPORTS / run_id).resolve()
    if not path.is_relative_to(REPORTS.resolve()) or not path.is_dir():
        raise HTTPException(404, 'Experiment not found.')
    return path


@router.get('/runs')
def runs():
    items = []
    if REPORTS.exists():
        for path in sorted(REPORTS.glob('run-*/summary.json'), reverse=True)[:50]:
            try:
                items.append(json.loads(path.read_text(encoding='utf-8')))
            except (OSError, ValueError):
                continue
    return {'items': items}


@router.get('/runs/{run_id}')
def detail(run_id: str):
    path = run_directory(run_id) / 'summary.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise HTTPException(409, 'The experiment has not written its summary yet.')


@router.get('/runs/{run_id}/cases')
def cases(run_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    path = run_directory(run_id) / 'results.jsonl'
    if not path.exists():
        return {'items': [], 'total': 0}
    rows = []
    with path.open(encoding='utf-8') as source:
        for line in source:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # Ignore the current partial line while the writer flushes.
    return {'items': rows[offset:offset+limit], 'total': len(rows), 'limit': limit, 'offset': offset}


@router.get('/runs/{run_id}/export/{filename}')
def export(run_id: str, filename: Literal['metrics.csv', 'results.json', 'dataset.json', 'summary.json', 'classifier.json']):
    path = run_directory(run_id) / filename
    if not path.exists():
        raise HTTPException(409, 'This export is available after the experiment finishes.')
    return FileResponse(path, filename='NovaBank-' + run_id + '-' + filename, media_type='text/csv' if filename.endswith('.csv') else 'application/json', headers={'Cache-Control': 'no-store'})


class Launch(IdentityInput):
    models: list[Literal['qwen2.5:7b', 'llama3.2:3b']] = Field(min_length=1, max_length=2)
    repetitions: int = Field(default=5, ge=1, le=5)
    ablations: bool = True
    smoke_test: bool = False


@router.post('/runs', status_code=202, dependencies=[Depends(require_permission('settings:write'))])
def launch(payload: Launch):
    global _process
    if _process is not None and _process.poll() is None:
        raise HTTPException(409, 'A research job is already running.')
    if any(r['status'] == 'RUNNING' and time.time() - r['updated_at'] < 600 for r in runs()['items']):
        raise HTTPException(409, 'A recent command-line research job is still running. Wait for it to finish.')
    REPORTS.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, '-m', 'research.run', '--models', *dict.fromkeys(payload.models), '--repetitions', str(payload.repetitions)]
    if payload.smoke_test:
        args += ['--limit', '2']
    elif payload.ablations:
        args.append('--ablations')
    # No shell interpolation, arbitrary file paths, model downloads, or bank DB argument.
    env = os.environ.copy()
    for key in ('DB_PATH', 'JWT_SECRET', 'MFA_ENCRYPTION_KEY'):
        env.pop(key, None)
    log = (REPORTS / ('launcher-' + uuid.uuid4().hex + '.log')).open('w', encoding='utf-8')
    try:
        _process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    finally:
        log.close()
    return {'message': 'Isolated experiment started. Refresh the run list to follow progress.'}
