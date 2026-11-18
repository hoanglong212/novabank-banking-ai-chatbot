"""Human-only assessment storage, separate from model-readable tool evidence."""
import json
from ..auth_crypto import encrypt_secret, decrypt_secret
from ..database import now


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=17').fetchone():
        return
    conn.execute('''CREATE TABLE ticket_assessments (run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
        ticket_id TEXT NOT NULL REFERENCES support_tickets(id),assessment_json TEXT NOT NULL,method TEXT NOT NULL,
        created_at TEXT NOT NULL,PRIMARY KEY(run_id,ticket_id))''')
    conn.execute('INSERT INTO schema_migrations VALUES (17,?)', (stamp,))


def save(conn, db, run, ticket_id, human, method):
    conn.execute('''INSERT INTO ticket_assessments VALUES (?,?,?,?,?) ON CONFLICT(run_id,ticket_id)
        DO UPDATE SET assessment_json=excluded.assessment_json,method=excluded.method,created_at=excluded.created_at''',
        (run['id'], ticket_id, encrypt_secret(db, json.dumps(human)), method, now()))


def human_view(conn, db, run_id):
    return [{'ticket_id': row['ticket_id'], 'assessment': json.loads(decrypt_secret(db, row['assessment_json'])), 'method': row['method']}
            for row in conn.execute('SELECT * FROM ticket_assessments WHERE run_id=? ORDER BY created_at', (run_id,))]
