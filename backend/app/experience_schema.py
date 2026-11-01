"""Version 2: transaction snapshots and customer notifications, preserving v1 data."""


def initialize_experience(conn, stamp: str):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=2').fetchone():
        return
    conn.execute('''CREATE TABLE transaction_details (
        transaction_id TEXT PRIMARY KEY REFERENCES transactions(id),
        transfer_id TEXT NOT NULL REFERENCES transfers(id),
        balance_after_vnd INTEGER CHECK(balance_after_vnd IS NULL OR
            (typeof(balance_after_vnd)='integer' AND balance_after_vnd>=0)),
        counterparty_name TEXT NOT NULL,
        counterparty_account TEXT NOT NULL,
        counterparty_bank TEXT NOT NULL,
        fee_vnd INTEGER NOT NULL DEFAULT 0 CHECK(typeof(fee_vnd)='integer' AND fee_vnd>=0)
    )''')
    conn.execute('CREATE INDEX idx_details_transfer ON transaction_details(transfer_id)')
    conn.execute('''CREATE TABLE notifications (
        id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
        transaction_id TEXT NOT NULL REFERENCES transactions(id),
        kind TEXT NOT NULL CHECK(kind IN ('MONEY_IN','MONEY_OUT')),
        title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL, read_at TEXT,
        UNIQUE(owner_id,transaction_id)
    )''')
    conn.execute('CREATE INDEX idx_notifications_owner ON notifications(owner_id,created_at,id)')
    # v1 has authoritative payer balances in banking_audit. Do not infer recipient
    # history by matching descriptions/timestamps, and do not fabricate old alerts.
    conn.execute('''INSERT INTO transaction_details
        SELECT t.transaction_id,t.id,
            (SELECT a.after_balance_vnd FROM banking_audit a
             WHERE a.resource_id=t.id AND a.action='TRANSFER_COMPLETED' LIMIT 1),
            t.to_name,t.to_account,t.to_bank,0
        FROM transfers t JOIN transactions x ON x.id=t.transaction_id WHERE t.status='COMPLETED'
    ''')
    # Charlie is the new zero-balance isolation-test/demo customer, never a rebase.
    row = conn.execute("SELECT balance_vnd FROM accounts WHERE id='ACC-CHARLIE-001'").fetchone()
    exists = conn.execute("SELECT 1 FROM ledger_accounts WHERE customer_account_id='ACC-CHARLIE-001'").fetchone()
    if row and not exists:
        if row[0] != 0:
            raise ValueError('Cannot add an unjournaled nonzero Charlie account')
        conn.execute("INSERT INTO ledger_accounts VALUES ('ACC-CHARLIE-001','ACC-CHARLIE-001','CUSTOMER')")
    for action in ('UPDATE', 'DELETE'):
        conn.execute(f'''CREATE TRIGGER transaction_details_no_{action.lower()} BEFORE {action} ON transaction_details
                         BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
    conn.execute('''CREATE TRIGGER transaction_details_no_replace BEFORE INSERT ON transaction_details
                    WHEN EXISTS(SELECT 1 FROM transaction_details WHERE transaction_id=NEW.transaction_id)
                    BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
    conn.execute('INSERT INTO schema_migrations VALUES (2,?)', (stamp,))
