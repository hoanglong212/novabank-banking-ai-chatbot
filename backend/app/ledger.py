"""Append-only journal and reconciliation for the local banking simulation.

Signed VND: a customer debit is negative and the matching credit positive.
Opening equity offsets balances imported at the migration boundary. Old demo
transaction history is retained, not presented as reconstructed ledger evidence.
"""
import json
import uuid
from datetime import datetime, timezone


SCHEMA = (
    '''CREATE TABLE ledger_accounts (
        id TEXT PRIMARY KEY,
        customer_account_id TEXT UNIQUE REFERENCES accounts(id),
        kind TEXT NOT NULL CHECK(kind IN ('CUSTOMER','OPENING_EQUITY','CLEARING')),
        CHECK((kind='CUSTOMER') = (customer_account_id IS NOT NULL))
    )''',
    '''CREATE TABLE ledger_entries (
        id TEXT PRIMARY KEY,
        journal_id TEXT NOT NULL,
        account_id TEXT NOT NULL REFERENCES ledger_accounts(id),
        amount_vnd INTEGER NOT NULL CHECK(typeof(amount_vnd)='integer' AND amount_vnd!=0),
        created_at TEXT NOT NULL,
        UNIQUE(journal_id,account_id)
    )''',
    'CREATE INDEX idx_ledger_account ON ledger_entries(account_id)',
    '''CREATE TABLE reconciliation_runs (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL, report_json TEXT NOT NULL
    )''',
    '''CREATE TABLE idempotency_keys (
        owner_id TEXT NOT NULL, key TEXT NOT NULL,
        transfer_id TEXT NOT NULL REFERENCES transfers(id),
        response_json TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(owner_id,key)
    )''',
    '''CREATE TABLE banking_audit (
        id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, action TEXT NOT NULL,
        resource_id TEXT NOT NULL, reason_code TEXT NOT NULL,
        before_balance_vnd INTEGER, after_balance_vnd INTEGER,
        created_at TEXT NOT NULL
    )''',
    'CREATE INDEX idx_transfer_daily ON transfers(owner_id,status,completed_at)',
)


def initialize_ledger(conn, stamp: str):
    """Version 1, inside Database.initialize's transaction; never rebase on restart."""
    conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=1').fetchone():
        return
    if conn.execute("SELECT 1 FROM accounts WHERE typeof(balance_vnd)!='integer' LIMIT 1").fetchone():
        raise ValueError('Legacy balances must be integer VND before ledger migration')
    conn.execute("ALTER TABLE accounts ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE' "
                 "CHECK(status IN ('ACTIVE','FROZEN','CLOSED'))")
    conn.execute('ALTER TABLE transfers ADD COLUMN failure_reason TEXT')
    for statement in SCHEMA:
        conn.execute(statement)
    conn.executemany('INSERT INTO ledger_accounts VALUES (?,NULL,?)',
                     [('SYS-OPENING', 'OPENING_EQUITY'), ('SYS-CLEARING', 'CLEARING')])
    for account in conn.execute('SELECT id,balance_vnd FROM accounts ORDER BY id').fetchall():
        account_id, balance = account
        conn.execute("INSERT INTO ledger_accounts VALUES (?,?,'CUSTOMER')", (account_id, account_id))
        if balance:
            conn.executemany('INSERT INTO ledger_entries VALUES (?,?,?,?,?)', [
                (uuid.uuid4().hex, 'OPENING:' + account_id, account_id, balance, stamp),
                (uuid.uuid4().hex, 'OPENING:' + account_id, 'SYS-OPENING', -balance, stamp),
            ])
    for table in ('ledger_entries', 'ledger_accounts', 'banking_audit', 'reconciliation_runs', 'idempotency_keys'):
        for action in ('UPDATE', 'DELETE'):
            conn.execute(f'''CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table}
                             BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
        conflict = 'owner_id=NEW.owner_id AND key=NEW.key' if table == 'idempotency_keys' else 'id=NEW.id'
        if table == 'ledger_entries':
            conflict += ' OR (journal_id=NEW.journal_id AND account_id=NEW.account_id)'
        if table == 'ledger_accounts':
            conflict += ' OR customer_account_id=NEW.customer_account_id'
        # REPLACE performs an implicit delete; delete triggers alone do not cover it.
        conn.execute(f'''CREATE TRIGGER {table}_no_replace BEFORE INSERT ON {table}
                         WHEN EXISTS(SELECT 1 FROM {table} WHERE {conflict})
                         BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
    for action in ('UPDATE', 'DELETE'):
        conn.execute(f'''CREATE TRIGGER completed_transactions_no_{action.lower()}
                         BEFORE {action} ON transactions WHEN OLD.status='COMPLETED'
                         BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
    conn.execute('''CREATE TRIGGER completed_transactions_no_replace BEFORE INSERT ON transactions
                    WHEN EXISTS(SELECT 1 FROM transactions WHERE id=NEW.id AND status='COMPLETED')
                    BEGIN SELECT RAISE(ABORT,'IMMUTABLE'); END''')
    for action in ('INSERT', 'UPDATE'):
        conn.execute(f'''CREATE TRIGGER accounts_integer_{action.lower()} BEFORE {action} ON accounts
                         WHEN typeof(NEW.balance_vnd)!='integer'
                         BEGIN SELECT RAISE(ABORT,'INTEGER_VND_REQUIRED'); END''')
    conn.execute('INSERT INTO schema_migrations VALUES (1,?)', (stamp,))


def reconcile(db) -> dict:
    """Check every journal and cached balance in one snapshot, persist the result."""
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        mismatches = [dict(row) for row in conn.execute('''
            SELECT a.id AS account_id,a.balance_vnd,COALESCE(SUM(e.amount_vnd),0) AS ledger_balance_vnd
            FROM accounts a LEFT JOIN ledger_accounts l ON l.customer_account_id=a.id
            LEFT JOIN ledger_entries e ON e.account_id=l.id GROUP BY a.id
            HAVING a.balance_vnd!=COALESCE(SUM(e.amount_vnd),0) OR l.id IS NULL ORDER BY a.id
        ''')]
        journals = [dict(row) for row in conn.execute('''
            SELECT journal_id,SUM(amount_vnd) AS total_vnd,COUNT(*) AS entry_count
            FROM ledger_entries GROUP BY journal_id
            HAVING SUM(amount_vnd)!=0 OR COUNT(*)<2 ORDER BY journal_id
        ''')]
        total = conn.execute('SELECT COALESCE(SUM(amount_vnd),0) FROM ledger_entries').fetchone()[0]
        result = dict(id=str(uuid.uuid4()), created_at=stamp,
                      balanced=not mismatches and not journals and total == 0,
                      ledger_total_vnd=total, mismatches=mismatches, unbalanced_journals=journals)
        conn.execute('INSERT INTO reconciliation_runs VALUES (?,?,?)',
                     (result['id'], stamp, json.dumps(result)))
    return result
