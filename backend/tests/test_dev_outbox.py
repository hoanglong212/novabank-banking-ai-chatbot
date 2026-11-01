import json
from pathlib import Path
import subprocess
import sys
from app.main import get_db
from .test_identity import register, token

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'dev-outbox.py'


def cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding='utf-8')


def test_outbox_requires_explicit_db_and_does_not_create_missing_file(tmp_path):
    assert cli().returncode != 0
    missing = tmp_path / 'missing.sqlite3'
    assert cli('--db', str(missing)).returncode != 0
    assert not missing.exists()


def test_cli_only_reveals_link_for_selected_message_and_loopback_origin(client):
    register(client)
    value = token('VERIFY_EMAIL')
    db = get_db().path
    result = cli('--db', db)
    assert result.returncode == 0, result.stderr
    assert value not in result.stdout
    row = json.loads(result.stdout)[0]
    selected = cli('--db', db, '--id', row['id'], '--origin', 'http://localhost:5173')
    assert selected.returncode == 0, selected.stderr
    assert json.loads(selected.stdout)['action_url'] == f'http://localhost:5173/#verify-email?token={value}'
    for origin in ['https://evil.example', 'http://localhost.evil.example', 'http://user@localhost:5173', 'http://localhost:5173/path']:
        assert cli('--db', db, '--id', row['id'], '--origin', origin).returncode != 0
    assert client.post('/api/auth/verify-email', json={'token': value}).status_code == 200
    used = cli('--db', db, '--id', row['id'])
    assert json.loads(used.stdout)['action_url'] is None and value not in used.stdout


def test_cli_exposes_live_otp_only_when_message_selected(client):
    from .test_sessions_mfa import begin, email_code, verify
    challenge = begin(client)
    code = email_code(challenge)
    db = get_db().path
    rows = json.loads(cli('--db', db).stdout)
    assert all('code' not in row and 'secret_text' not in row for row in rows)
    selected = json.loads(cli('--db', db, '--id', rows[0]['id']).stdout)
    assert selected['code'] == code and 'secret_text' not in selected
    assert verify(client, challenge, code).status_code == 200
    assert json.loads(cli('--db', db, '--id', rows[0]['id']).stdout)['code'] is None
