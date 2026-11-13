"""Version 4: persisted login controls, action-bound MFA and revocable sessions."""


def initialize_sessions(conn, stamp):
    # Trusted devices skip login MFA; only token hashes are stored. Additive, so no version bump.
    conn.execute('''CREATE TABLE IF NOT EXISTS trusted_devices (token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id), auth_version INTEGER NOT NULL,
        created_at INTEGER NOT NULL, last_used_at INTEGER NOT NULL)''')
    # Self-registered customers must set a transaction PIN (or authenticator) before transacting.
    conn.execute('CREATE TABLE IF NOT EXISTS totp_required (user_id TEXT PRIMARY KEY REFERENCES users(id))')
    # Customer-chosen transaction PIN (PBKDF2 hash only), with its own failure lockout.
    conn.execute('''CREATE TABLE IF NOT EXISTS transaction_pins (user_id TEXT PRIMARY KEY REFERENCES users(id),
        pin_hash TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0, locked_until INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL)''')
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=4').fetchone():
        return
    statements = [
        '''CREATE TABLE user_sessions (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), auth_version INTEGER NOT NULL,
            created_at INTEGER NOT NULL, last_active_at INTEGER NOT NULL, absolute_expires_at INTEGER NOT NULL,
            revoked_at INTEGER, revoke_reason TEXT, ip TEXT NOT NULL, user_agent TEXT NOT NULL, method TEXT NOT NULL)''',
        'CREATE INDEX idx_sessions_user ON user_sessions(user_id,created_at)',
        '''CREATE TABLE refresh_tokens (token_hash TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES user_sessions(id),
            created_at INTEGER NOT NULL, used_at INTEGER)''',
        'CREATE INDEX idx_refresh_session ON refresh_tokens(session_id)',
        '''CREATE TABLE login_lockouts (subject_hash TEXT PRIMARY KEY, failures INTEGER NOT NULL,
            window_start INTEGER NOT NULL, locked_until INTEGER NOT NULL DEFAULT 0)''',
        '''CREATE TABLE login_attempts (id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id),
            created_at INTEGER NOT NULL, result TEXT NOT NULL, method TEXT NOT NULL, ip TEXT NOT NULL, user_agent TEXT NOT NULL)''',
        'CREATE INDEX idx_attempts_user ON login_attempts(user_id,created_at)',
        '''CREATE TABLE mfa_challenges (id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
            auth_version INTEGER NOT NULL, purpose TEXT NOT NULL CHECK(purpose IN ('LOGIN','DISABLE_TOTP')),
            session_id TEXT, method TEXT NOT NULL CHECK(method IN ('email','totp')), otp_hash TEXT, otp_expires_at INTEGER,
            created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            sends INTEGER NOT NULL DEFAULT 0, sent_at INTEGER, consumed_at INTEGER, ip TEXT NOT NULL, user_agent TEXT NOT NULL)''',
        'CREATE INDEX idx_challenges_user ON mfa_challenges(user_id,purpose)',
        '''CREATE TABLE mfa_settings (user_id TEXT PRIMARY KEY REFERENCES users(id), secret_encrypted TEXT,
            last_step INTEGER NOT NULL DEFAULT -1, pending_secret TEXT, pending_expires_at INTEGER,
            pending_session_id TEXT, pending_attempts INTEGER NOT NULL DEFAULT 0)''',
        'ALTER TABLE dev_outbox ADD COLUMN secret_text TEXT',
        'ALTER TABLE dev_outbox ADD COLUMN challenge_id TEXT',
        'ALTER TABLE dev_outbox ADD COLUMN body TEXT',
        'CREATE INDEX idx_outbox_challenge ON dev_outbox(challenge_id)',
    ]
    for sql in statements:
        conn.execute(sql)
    conn.execute('INSERT INTO schema_migrations VALUES (4,?)', (stamp,))
