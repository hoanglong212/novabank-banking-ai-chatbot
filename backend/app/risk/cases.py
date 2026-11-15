import json
import uuid
from ..database import now

FEATURES = ('tool', 'tier', 'context_label', 'recipient_new', 'amount_bucket', 'config')


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=15').fetchone():
        return
    conn.execute('''CREATE TABLE risk_cases (id TEXT PRIMARY KEY,created_at TEXT NOT NULL,
        run_id TEXT UNIQUE NOT NULL,features_json TEXT NOT NULL,decision TEXT NOT NULL,score INTEGER NOT NULL)''')
    conn.execute('''CREATE TABLE approval_risk (approval_id TEXT PRIMARY KEY REFERENCES tool_approvals(id) ON DELETE CASCADE,
        run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE, score INTEGER NOT NULL,band TEXT NOT NULL,
        not_before INTEGER NOT NULL,features_json TEXT NOT NULL,origins_json TEXT NOT NULL,rule_ids_json TEXT NOT NULL)''')
    conn.execute("ALTER TABLE agent_runs ADD COLUMN risk_features_json TEXT NOT NULL DEFAULT '{}'")
    conn.execute('ALTER TABLE agent_runs ADD COLUMN risk_score INTEGER NOT NULL DEFAULT 0')
    conn.execute("ALTER TABLE agent_runs ADD COLUMN risk_decision TEXT NOT NULL DEFAULT 'allow'")
    conn.execute('INSERT INTO schema_migrations VALUES (15,?)', (stamp,))


def record(conn, run_id, features, decision, score):
    safe = {key: features[key] for key in FEATURES if key in features}
    conn.execute('INSERT INTO risk_cases VALUES (?,?,?,?,?,?) ON CONFLICT(run_id) DO NOTHING',
        (uuid.uuid4().hex, now(), run_id, json.dumps(safe), decision, score))


def nearest(conn, features, k=5):
    query = {str(key) + '=' + str(features.get(key)) for key in FEATURES}
    candidates = []
    # Bound history retrieval; no embeddings, text, customer identifiers or model calls.
    for row in conn.execute('SELECT rowid AS sequence,* FROM risk_cases ORDER BY created_at DESC,rowid DESC LIMIT 5000'):
        item = dict(row)
        old = json.loads(item.pop('features_json'))
        tokens = {str(key) + '=' + str(old.get(key)) for key in FEATURES}
        item['distance'] = 1 - len(query & tokens) / len(query | tokens)
        candidates.append(item)
    return sorted(candidates, key=lambda item: (item['distance'], -item['sequence']))[:min(max(k, 0), 5)]


def finish(conn, run_id):
    row = conn.execute('SELECT risk_features_json,risk_decision,risk_score FROM agent_runs WHERE id=?', (run_id,)).fetchone()
    if row:
        record(conn, run_id, json.loads(row[0]), row[1], row[2])
