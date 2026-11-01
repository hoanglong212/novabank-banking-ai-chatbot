"""Version 7: delegated agent runs, approvals, trace and retrieval chunks."""
from .faq import FAQ


def initialize_agent_termination(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=9').fetchone():
        return
    conn.execute('ALTER TABLE agent_runs ADD COLUMN termination_reason TEXT')
    conn.execute('INSERT INTO schema_migrations VALUES (9,?)', (stamp,))


def initialize_agent(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=7').fetchone():
        return
    statements = [
        '''CREATE TABLE agent_runs (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            session_id TEXT NOT NULL REFERENCES user_sessions(id), auth_version INTEGER NOT NULL,
            status TEXT NOT NULL, profile TEXT NOT NULL, model TEXT NOT NULL, bound_request_json TEXT NOT NULL,
            created_at TEXT NOT NULL, expires_at INTEGER NOT NULL, completed_at TEXT,
            latency_ms INTEGER, input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0,
            response_source TEXT, answer TEXT, vault_json TEXT NOT NULL DEFAULT '{}')''',
        '''CREATE TABLE agent_calls (id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, name TEXT NOT NULL, arguments_json TEXT NOT NULL,
            decision TEXT NOT NULL, reason TEXT NOT NULL, latency_ms INTEGER NOT NULL,
            result_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(run_id,ordinal))''',
        '''CREATE TABLE tool_approvals (id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
            owner_id TEXT NOT NULL REFERENCES users(id), session_id TEXT NOT NULL REFERENCES user_sessions(id),
            name TEXT NOT NULL, arguments_json TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, expires_at INTEGER NOT NULL, response_json TEXT)''',
        '''CREATE TABLE knowledge_chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, text TEXT NOT NULL, embedding_json TEXT NOT NULL, embedding_model TEXT NOT NULL,
            document_hash TEXT NOT NULL, UNIQUE(document_id,ordinal))''',
        'CREATE INDEX idx_agent_runs_owner ON agent_runs(owner_id,created_at)',
        'CREATE INDEX idx_approvals_owner ON tool_approvals(owner_id,status)',
    ]
    for sql in statements:
        conn.execute(sql)
    policies = [
        ('payments', 'NovaBank transfer rules', 'NovaBank is a fictional bank. Transfers use integer VND, from 1,000 to 100,000,000 VND per payment and a default 200,000,000 VND daily limit. An administrator can lower these limits and configure a fee. The reviewed draft fixes its fee. Internal transfers settle immediately after OTP confirmation. Simulated external transfers remain pending for about five seconds; account numbers ending in 0000 are rejected and refunded including fees. Never use these account IDs to send real money.'),
        ('savings', 'Term savings', 'NovaBank offers simulated terms of 3, 6 and 12 months at annual rates of 4.5%, 5% and 6%. Minimum deposit is 100,000 VND. Simple interest is principal times annual basis points times months divided by 120,000, rounded down to integer VND. Interest is paid when withdrawing at or after maturity. Early withdrawal returns principal with zero interest. The original funding account receives withdrawals. Confirm deposits and withdrawals with an OTP.'),
        ('cards', 'Debit and credit cards', 'Debit purchases use the payment account balance. Simulated credit cards have a 20,000,000 VND limit; purchases increase outstanding debt and repayments reduce it. Freeze or unfreeze cards in Explore, Cards after confirming a code. Frozen cards cannot make purchases. No real card numbers, CVVs or payment networks are used.'),
        ('bills', 'Paying bills', 'Explore, Pay bills contains fictional electricity, water, internet and mobile invoices. Review the provider, amount and funding account, then enter the email verification code. A paid bill cannot be paid again. Saved bills produce a reminder shortly before the due date. These payments do not pay any real utility provider.'),
        ('security', 'Sessions and verification', 'Sign-in requires a password and an email code, or an enrolled authenticator. Access credentials last five minutes; inactivity ends a session after five minutes and absolute lifetime is eight hours. Active input refreshes idle activity; polling does not. Profile, Security Center lists sessions and sign-in history. Changing a password ends all sessions. Never put passwords, OTPs or recovery codes into chat.'),
        ('support', 'Contacting support', 'Open Explore, Help and support to create a ticket, read replies and upload up to five attachments of at most 2 MB each. PNG, JPEG, PDF and UTF-8 text files are accepted. Staff can assign tickets and change their status. The assistant can propose a ticket, but the customer must approve it before it is created.'),
        ('qr-demo', 'NovaBank demo QR', 'NovaBank QR codes use a private NBQR1 format with a signed payload. They are not VietQR, NAPAS or EMV payment instructions and cannot be paid using a real banking app. Create a code for your payment account in Explore, Demo QR. Upload its original PNG or paste its text to populate the transfer review form. A code never authorizes a payment.'),
        ('budgets', 'Spending and statements', 'Explore shows spending by category and monthly budgets. Only completed payments count; savings principal movements and credit repayments are excluded to avoid double counting. Credit purchases count when made. Statements can be exported as PDF or CSV for up to one year. Some old sample transactions predate the ledger and have no recorded balance snapshot.'),
    ]
    for key, title, content in policies:
        conn.execute('''INSERT INTO knowledge_documents
            (id,title,content,source,trust_level,status,created_at,updated_at) VALUES (?,?,?,?,'approved','PUBLISHED',?,?)''',
            ('KB-' + key, title, content, 'NovaBank simulation policy · ' + key, stamp, stamp))
    conn.execute('INSERT INTO schema_migrations VALUES (7,?)', (stamp,))
