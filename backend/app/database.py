"""SQLite is the source of truth for persisted chat history and audit events."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


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
            ''')

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
        # Event store holds tool metadata. Do not add tool results or secrets here.
        event = dict(id=str(uuid.uuid4()), conversation_id=conversation_id, tool_name=tool_name,
                     arguments_json=json.dumps(arguments, ensure_ascii=False)[:1500],
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

    def ticket_count(self, owner_id: str):
        with self.connect() as conn:
            return conn.execute('SELECT COUNT(*) FROM support_tickets WHERE owner_id=?', (owner_id,)).fetchone()[0]
