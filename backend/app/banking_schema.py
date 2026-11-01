"""Version 5: customer products, action confirmations and service workflows.

New tables avoid rewriting existing accounts, immutable journals or history.
Internal product subledgers use the existing CLEARING ledger-account category.
"""
import uuid


def initialize_banking(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=5').fetchone():
        return
    statements = [
        '''CREATE TABLE customer_profiles (user_id TEXT PRIMARY KEY REFERENCES users(id),
            phone TEXT NOT NULL DEFAULT '', phone_verified_at TEXT, kyc_status TEXT NOT NULL DEFAULT 'UNVERIFIED')''',
        '''CREATE TABLE account_labels (account_id TEXT PRIMARY KEY REFERENCES accounts(id), nickname TEXT NOT NULL)''',
        '''CREATE TABLE beneficiaries (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            account_id TEXT NOT NULL, bank TEXT NOT NULL, holder_name TEXT NOT NULL, nickname TEXT NOT NULL,
            trust_level TEXT NOT NULL DEFAULT 'untrusted', created_at TEXT NOT NULL, UNIQUE(owner_id,account_id,bank))''',
        '''CREATE TABLE action_challenges (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            session_id TEXT NOT NULL REFERENCES user_sessions(id), auth_version INTEGER NOT NULL,
            kind TEXT NOT NULL, payload_json TEXT NOT NULL, otp_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            consumed_at INTEGER, idempotency_key TEXT, response_json TEXT,
            UNIQUE(owner_id,idempotency_key))''',
        '''CREATE TABLE cards (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            account_id TEXT NOT NULL REFERENCES accounts(id), kind TEXT NOT NULL CHECK(kind IN ('DEBIT','CREDIT')),
            last_four TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('ACTIVE','FROZEN')),
            credit_limit_vnd INTEGER NOT NULL DEFAULT 0, outstanding_vnd INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, CHECK(outstanding_vnd>=0 AND outstanding_vnd<=credit_limit_vnd))''',
        '''CREATE TABLE card_transactions (id TEXT PRIMARY KEY, card_id TEXT NOT NULL REFERENCES cards(id),
            amount_vnd INTEGER NOT NULL CHECK(typeof(amount_vnd)='integer' AND amount_vnd>0),
            kind TEXT NOT NULL, merchant TEXT NOT NULL, journal_id TEXT NOT NULL, created_at TEXT NOT NULL)''',
        '''CREATE TABLE bills (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            provider TEXT NOT NULL, category TEXT NOT NULL, customer_code TEXT NOT NULL,
            amount_vnd INTEGER NOT NULL CHECK(typeof(amount_vnd)='integer' AND amount_vnd>0), due_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('UNPAID','PAID')), saved INTEGER NOT NULL DEFAULT 0,
            transaction_id TEXT REFERENCES transactions(id), paid_at TEXT)''',
        '''CREATE TABLE savings (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            account_id TEXT NOT NULL REFERENCES accounts(id), label TEXT NOT NULL,
            principal_vnd INTEGER NOT NULL CHECK(typeof(principal_vnd)='integer' AND principal_vnd>=100000),
            term_months INTEGER NOT NULL, rate_bps INTEGER NOT NULL, opened_at TEXT NOT NULL,
            maturity_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('ACTIVE','CLOSED')),
            closed_at TEXT, interest_paid_vnd INTEGER NOT NULL DEFAULT 0)''',
        '''CREATE TABLE savings_events (id TEXT PRIMARY KEY, savings_id TEXT NOT NULL REFERENCES savings(id),
            kind TEXT NOT NULL, amount_vnd INTEGER NOT NULL, transaction_id TEXT NOT NULL REFERENCES transactions(id), created_at TEXT NOT NULL)''',
        '''CREATE TABLE savings_goals (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            label TEXT NOT NULL, target_vnd INTEGER NOT NULL CHECK(typeof(target_vnd)='integer' AND target_vnd>0),
            target_date TEXT NOT NULL, savings_id TEXT REFERENCES savings(id))''',
        '''CREATE TABLE product_transaction_details (transaction_id TEXT PRIMARY KEY REFERENCES transactions(id),
            journal_id TEXT NOT NULL, kind TEXT NOT NULL, resource_id TEXT NOT NULL,
            balance_after_vnd INTEGER NOT NULL, counterparty_name TEXT NOT NULL, fee_vnd INTEGER NOT NULL DEFAULT 0)''',
        '''CREATE TABLE service_notifications (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
            kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, resource_id TEXT,
            transaction_id TEXT REFERENCES transactions(id), created_at TEXT NOT NULL, read_at TEXT,
            dedupe_key TEXT UNIQUE)''',
        '''CREATE TABLE budgets (owner_id TEXT NOT NULL REFERENCES users(id), month TEXT NOT NULL, category TEXT NOT NULL,
            amount_vnd INTEGER NOT NULL CHECK(typeof(amount_vnd)='integer' AND amount_vnd>0), PRIMARY KEY(owner_id,month,category))''',
        '''CREATE TABLE transaction_categories (transaction_id TEXT PRIMARY KEY REFERENCES transactions(id), category TEXT NOT NULL)''',
        '''CREATE TABLE bank_settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL)''',
        '''CREATE TABLE ticket_messages (id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES support_tickets(id),
            author_id TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL, created_at TEXT NOT NULL)''',
        '''CREATE TABLE ticket_assignments (ticket_id TEXT PRIMARY KEY REFERENCES support_tickets(id),
            assigned_to TEXT REFERENCES users(id), category TEXT NOT NULL DEFAULT 'GENERAL')''',
        '''CREATE TABLE ticket_attachments (id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES support_tickets(id),
            owner_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL, media_type TEXT NOT NULL,
            content BLOB NOT NULL, created_at TEXT NOT NULL)''',
        '''CREATE TABLE knowledge_documents (id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
            source TEXT NOT NULL, trust_level TEXT NOT NULL CHECK(trust_level IN ('approved','untrusted')),
            status TEXT NOT NULL CHECK(status IN ('DRAFT','PUBLISHED')), embedding_json TEXT,
            embedding_model TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''',
    ]
    for sql in statements:
        conn.execute(sql)
    for name in ('BILLS', 'SAVINGS', 'MERCHANTS', 'FEES', 'INTEREST'):
        conn.execute("INSERT INTO ledger_accounts VALUES (?,NULL,'CLEARING')", ('SYS-' + name,))
    for key, value in {'transfer_fee_vnd': '0', 'transfer_limit_vnd': '100000000',
                       'daily_limit_vnd': '200000000', 'agent_enabled': 'true'}.items():
        conn.execute('INSERT INTO bank_settings VALUES (?,?,?)', (key, value, stamp))
    for table in ('card_transactions', 'savings_events', 'product_transaction_details'):
        key = 'transaction_id' if table == 'product_transaction_details' else 'id'
        for action in ('UPDATE', 'DELETE'):
            conn.execute(f'''CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table}
                BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
        conn.execute(f'''CREATE TRIGGER {table}_no_replace BEFORE INSERT ON {table}
            WHEN EXISTS(SELECT 1 FROM {table} WHERE {key}=NEW.{key})
            BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
    conn.execute('INSERT INTO schema_migrations VALUES (5,?)', (stamp,))


def ensure_products(conn, owner, stamp):
    """Provision fictional products once, including for newly verified customers."""
    from datetime import date, timedelta
    account = conn.execute('SELECT id FROM accounts WHERE owner_id=? ORDER BY id LIMIT 1', (owner,)).fetchone()
    if not account:
        return
    for kind in ('DEBIT', 'CREDIT'):
        card_id = 'CARD-' + owner + '-' + kind
        conn.execute('INSERT OR IGNORE INTO cards VALUES (?,?,?,?,?,?,?,?,?)',
                     (card_id, owner, account[0], kind, '1001' if kind == 'DEBIT' else '2001', 'ACTIVE',
                      0 if kind == 'DEBIT' else 20_000_000, 0, stamp))
        if kind == 'CREDIT':
            ledger_id = 'CREDIT:' + card_id
            if not conn.execute('SELECT 1 FROM ledger_accounts WHERE id=?', (ledger_id,)).fetchone():
                conn.execute("INSERT INTO ledger_accounts VALUES (?,NULL,'CLEARING')", (ledger_id,))
    due = (date.fromisoformat(stamp[:10]) + timedelta(days=7)).isoformat()
    providers = [('electricity', 'Nova Energy', 450000), ('water', 'Nova Water', 120000),
                 ('internet', 'Nova Fiber', 250000), ('mobile', 'Nova Mobile', 100000)]
    for category, provider, amount in providers:
        conn.execute('INSERT OR IGNORE INTO bills VALUES (?,?,?,?,?,?,?,\'UNPAID\',0,NULL,NULL)',
                     ('BILL-' + owner + '-' + category, owner, provider, category, 'DEMO-' + owner, amount, due))
