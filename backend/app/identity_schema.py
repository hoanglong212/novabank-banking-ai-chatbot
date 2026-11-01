"""Version 3: persisted identities and local, simulated email delivery."""


def initialize_identity(conn, stamp: str):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=3').fetchone():
        return
    conn.execute('''CREATE TABLE users (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer','support','operations','auditor','admin')),
        status TEXT NOT NULL CHECK(status IN ('PENDING','ACTIVE','DISABLED')),
        auth_version INTEGER NOT NULL DEFAULT 0 CHECK(auth_version>=0), created_at TEXT NOT NULL
    )''')
    conn.execute('''CREATE TABLE identity_tokens (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
        purpose TEXT NOT NULL CHECK(purpose IN ('VERIFY_EMAIL','RESET_PASSWORD')),
        expires_at INTEGER NOT NULL, consumed_at INTEGER
    )''')
    conn.execute('CREATE INDEX idx_identity_tokens_user ON identity_tokens(user_id,purpose)')
    conn.execute('''CREATE TABLE dev_outbox (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), recipient TEXT NOT NULL,
        kind TEXT NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER, action_path TEXT
    )''')
    conn.execute('CREATE INDEX idx_dev_outbox_user ON dev_outbox(user_id,kind)')
    conn.execute('''CREATE TABLE identity_limits (
        scope TEXT NOT NULL, subject_hash TEXT NOT NULL, starts_at INTEGER NOT NULL,
        attempts INTEGER NOT NULL, PRIMARY KEY(scope,subject_hash,starts_at)
    )''')
    conn.execute('''CREATE TABLE identity_audit (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
        action TEXT NOT NULL, created_at INTEGER NOT NULL
    )''')
    # Seed once only: startup must never restore a password changed by recovery.
    from .auth import DEMO_USERS
    conn.executemany('INSERT INTO users VALUES (?,?,?,?,?,?,0,?)', [
        (u.id, u.name, f'{u.id}@novabank.test', u.password_hash, u.role, 'ACTIVE', stamp)
        for u in DEMO_USERS
    ])
    conn.execute('INSERT INTO schema_migrations VALUES (3,?)', (stamp,))
