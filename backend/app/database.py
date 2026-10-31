"""SQLite is the source of truth for persisted chat history and audit events."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .guard import mask


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


# Fictional seed data; balances then change only through transfers.post().
SEED_ACCOUNTS = [
    ('ACC-ALICE-001', 'alice', 'ALICE NGUYEN', 12500000),
    ('ACC-BOB-001', 'bob', 'BOB TRAN', 8750000),
]
SEED_TRANSACTIONS = [
    ('TX-1001', 'ACC-ALICE-001', 300000, 'out', 'COMPLETED', 'Transfer to Minh Anh', '2026-10-24'),
    ('TX-1002', 'ACC-ALICE-001', 950000, 'out', 'PENDING', 'Electricity bill', '2026-10-25'),
    ('TX-1003', 'ACC-ALICE-001', 45000, 'out', 'COMPLETED', 'Coffee shop', '2026-10-26'),
    ('TX-1004', 'ACC-ALICE-001', 15000000, 'in', 'COMPLETED', 'Salary credit', '2026-10-20'),
    ('TX-2001', 'ACC-BOB-001', 200000, 'out', 'COMPLETED', 'Transfer to Gia Bao', '2026-10-23'),
    ('TX-2002', 'ACC-BOB-001', 120000, 'out', 'COMPLETED', 'Ride-hailing trip', '2026-10-25'),
    ('TX-2003', 'ACC-BOB-001', 5000000, 'in', 'COMPLETED', 'Freelance payment', '2026-10-21'),
]
TX_COLUMNS = 't.id, t.account_id, t.amount_vnd, t.direction, t.status, t.description, t.date'


class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA busy_timeout = 5000')
        return conn

    def initialize(self):
        with self.connect() as conn:
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS conversations (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              title TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner_id, updated_at);
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
              role TEXT NOT NULL CHECK(role IN ('user','assistant')),
              content TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
            CREATE TABLE IF NOT EXISTS tool_events (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
              tool_name TEXT NOT NULL,
              arguments_json TEXT NOT NULL,
              decision TEXT NOT NULL CHECK(decision IN ('ALLOW','DENY')),
              reason_code TEXT NOT NULL,
              executed INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              subject TEXT NOT NULL,
              description TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accounts (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              holder_name TEXT NOT NULL,
              balance_vnd INTEGER NOT NULL CHECK(balance_vnd >= 0)
            );
            CREATE TABLE IF NOT EXISTS transactions (
              id TEXT PRIMARY KEY,
              account_id TEXT NOT NULL REFERENCES accounts(id),
              amount_vnd INTEGER NOT NULL CHECK(amount_vnd > 0),
              direction TEXT NOT NULL CHECK(direction IN ('in','out')),
              status TEXT NOT NULL,
              description TEXT NOT NULL,
              date TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id, date);
            CREATE TABLE IF NOT EXISTS transfers (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              from_account TEXT NOT NULL REFERENCES accounts(id),
              to_bank TEXT NOT NULL,
              to_account TEXT NOT NULL,
              to_name TEXT NOT NULL,
              internal INTEGER NOT NULL,
              amount_vnd INTEGER NOT NULL CHECK(amount_vnd > 0),
              content TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('PENDING_OTP','COMPLETED','FAILED')),
              otp_hash TEXT,
              otp_expires_at TEXT,
              otp_attempts INTEGER NOT NULL DEFAULT 0,
              transaction_id TEXT,
              created_at TEXT NOT NULL,
              completed_at TEXT
            );
            ''')
            conn.executemany('INSERT OR IGNORE INTO accounts VALUES (?,?,?,?)', SEED_ACCOUNTS)
            conn.executemany('INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?,?,?)',
                             [(*t, t[-1] + 'T00:00:00+00:00') for t in SEED_TRANSACTIONS])

    def create_conversation(self, owner_id: str, title: str):
        result = dict(id=str(uuid.uuid4()), owner_id=owner_id, title=title, created_at=now(), updated_at=now())
        with self.connect() as conn:
            conn.execute('INSERT INTO conversations VALUES (:id,:owner_id,:title,:created_at,:updated_at)', result)
        return result

    def list_conversations(self, owner_id: str):
        with self.connect() as conn:
            return [dict(x) for x in conn.execute('SELECT * FROM conversations WHERE owner_id=? ORDER BY updated_at DESC', (owner_id,)).fetchall()]

    def get_conversation(self, conversation_id: str, owner_id: str):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM conversations WHERE id=? AND owner_id=?', (conversation_id, owner_id)).fetchone()
            return dict(row) if row else None

    def delete_conversation(self, conversation_id: str, owner_id: str):
        with self.connect() as conn:
            cursor = conn.execute('DELETE FROM conversations WHERE id=? AND owner_id=?', (conversation_id, owner_id))
            return cursor.rowcount > 0

    def append_message(self, conversation_id: str, role: str, content: str):
        value = dict(id=str(uuid.uuid4()), conversation_id=conversation_id, role=role, content=content, created_at=now())
        with self.connect() as conn:
            conn.execute('INSERT INTO messages VALUES (:id,:conversation_id,:role,:content,:created_at)', value)
            conn.execute('UPDATE conversations SET updated_at=? WHERE id=?', (now(), conversation_id))
        return value

    def list_messages(self, conversation_id: str):
        with self.connect() as conn:
            return [dict(x) for x in conn.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at, rowid', (conversation_id,)).fetchall()]

    def add_event(self, conversation_id: str, tool_name: str, arguments: dict, decision: str, reason_code: str, executed: bool):
        # Event store holds tool metadata. Do not add tool results or secrets here; PII is masked.
        event = dict(id=str(uuid.uuid4()), conversation_id=conversation_id, tool_name=tool_name,
                     arguments_json=json.dumps(mask(arguments), ensure_ascii=False)[:1500],
                     decision=decision, reason_code=reason_code, executed=int(executed), created_at=now())
        with self.connect() as conn:
            conn.execute('''INSERT INTO tool_events (id,conversation_id,tool_name,arguments_json,decision,reason_code,executed,created_at)
                            VALUES (:id,:conversation_id,:tool_name,:arguments_json,:decision,:reason_code,:executed,:created_at)''', event)
        return event

    def list_events(self, conversation_id: str):
        with self.connect() as conn:
            rows = conn.execute('SELECT * FROM tool_events WHERE conversation_id=? ORDER BY created_at,rowid', (conversation_id,)).fetchall()
            return [dict(**{k: x[k] for k in x.keys() if k != 'arguments_json'}, arguments=json.loads(x['arguments_json'])) for x in rows]

    def create_ticket(self, owner_id: str, subject: str, description: str):
        value = dict(id='TKT-' + uuid.uuid4().hex[:8].upper(), owner_id=owner_id, subject=subject,
                     description=description, status='OPEN', created_at=now())
        with self.connect() as conn:
            conn.execute('INSERT INTO support_tickets VALUES (:id,:owner_id,:subject,:description,:status,:created_at)', value)
        return value

    def accounts_of(self, owner_id: str):
        with self.connect() as conn:
            return [dict(x) for x in conn.execute('SELECT * FROM accounts WHERE owner_id=? ORDER BY id', (owner_id,)).fetchall()]

    def account(self, account_id: str):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
            return dict(row) if row else None

    def transaction(self, transaction_id: str):
        with self.connect() as conn:
            row = conn.execute(f'SELECT {TX_COLUMNS}, a.owner_id FROM transactions t JOIN accounts a ON a.id=t.account_id '
                               'WHERE t.id=?', (transaction_id,)).fetchone()
            return dict(row) if row else None

    def transactions_of(self, owner_id: str, limit: int = -1):
        with self.connect() as conn:
            return [dict(x) for x in conn.execute(
                f'SELECT {TX_COLUMNS} FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE a.owner_id=? '
                'ORDER BY t.date DESC, t.created_at DESC LIMIT ?', (owner_id, limit)).fetchall()]

    def create_transfer(self, transfer: dict):
        with self.connect() as conn:
            conn.execute('INSERT INTO transfers (id,owner_id,from_account,to_bank,to_account,to_name,internal,amount_vnd,'
                         'content,status,created_at) VALUES (:id,:owner_id,:from_account,:to_bank,:to_account,:to_name,'
                         ':internal,:amount_vnd,:content,:status,:created_at)', transfer)

    def get_transfer(self, transfer_id: str, owner_id: str):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM transfers WHERE id=? AND owner_id=?', (transfer_id, owner_id)).fetchone()
            return dict(row) if row else None

    def ticket_count(self, owner_id: str):
        with self.connect() as conn:
            return conn.execute('SELECT COUNT(*) FROM support_tickets WHERE owner_id=?', (owner_id,)).fetchone()[0]
