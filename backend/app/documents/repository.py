"""The only SQL access to documents/chunks. Every data operation is owner-scoped."""
import json
import uuid
from contextlib import closing
from fastapi import HTTPException
from ..database import now
from ..identity import transaction, quota
from ..session_security import timestamp

METADATA = 'id,filename_display,mime,size_bytes,sha256,status,status_reason,created_at'

def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=21').fetchone():
        return
    conn.execute("""CREATE TABLE documents (
        id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), filename_display TEXT NOT NULL,
        mime TEXT NOT NULL, size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('processing','ready','quarantined','scan_failed','rejected')),
        status_reason TEXT, created_at TEXT NOT NULL, deleted_at TEXT,
        UNIQUE(id,owner_id))""")
    conn.execute("""CREATE TABLE doc_chunks (
        id TEXT PRIMARY KEY, document_id TEXT NOT NULL, owner_id TEXT NOT NULL, seq INTEGER NOT NULL,
        text TEXT NOT NULL, embedding BLOB NOT NULL, screen_result TEXT NOT NULL,
        FOREIGN KEY(document_id,owner_id) REFERENCES documents(id,owner_id) ON DELETE CASCADE,
        UNIQUE(document_id,seq))""")
    conn.execute('CREATE INDEX documents_owner ON documents(owner_id,deleted_at,created_at)')
    conn.execute('CREATE INDEX chunks_owner_doc ON doc_chunks(owner_id,document_id)')
    conn.execute('INSERT INTO schema_migrations VALUES (21,?)', (stamp,))


class Repository:
    def __init__(self, db, owner):
        if not owner:
            raise ValueError('Owner required')
        self.db, self.owner = db, owner

    def rate_limit(self):
        with transaction(self.db) as conn:
            allowed = quota(conn, 'document-upload', self.owner, 10, 300, timestamp())
        if not allowed:
            raise HTTPException(429, 'UPLOAD_RATE_LIMIT')

    def reserve(self, filename, mime, size, digest):
        with transaction(self.db) as conn:
            retry = conn.execute("""SELECT id FROM documents WHERE owner_id=? AND sha256=?
                AND status='scan_failed' AND deleted_at IS NULL LIMIT 1""", (self.owner, digest)).fetchone()
            if retry:
                key = retry[0]
                conn.execute("""UPDATE documents SET status='processing',status_reason=NULL,filename_display=?
                    WHERE id=? AND owner_id=? AND deleted_at IS NULL""", (filename, key, self.owner))
                return key
            count = conn.execute('SELECT COUNT(*) FROM documents WHERE owner_id=? AND deleted_at IS NULL', (self.owner,)).fetchone()[0]
            if count >= 20:
                raise HTTPException(409, 'DOCUMENT_LIMIT')
            key = str(uuid.uuid4())
            conn.execute("""INSERT INTO documents
                (id,owner_id,filename_display,mime,size_bytes,sha256,status,created_at)
                VALUES (?,?,?,?,?,?,'processing',?)""", (key, self.owner, filename, mime, size, digest, now()))
            return key

    def finish(self, key, status, reason, chunks=(), vectors=(), model=''):
        with transaction(self.db) as conn:
            changed = conn.execute("""UPDATE documents SET status=?,status_reason=?
                WHERE id=? AND owner_id=? AND deleted_at IS NULL AND status='processing'""",
                (status, reason, key, self.owner)).rowcount
            if not changed:
                raise HTTPException(404, 'DOCUMENT_UNAVAILABLE')
            conn.execute('DELETE FROM doc_chunks WHERE document_id=? AND owner_id=?', (key, self.owner))
            for seq, (text, vector) in enumerate(zip(chunks, vectors)):
                conn.execute("""INSERT INTO doc_chunks (id,document_id,owner_id,seq,text,embedding,screen_result)
                    VALUES (?,?,?,?,?,?,?)""", (str(uuid.uuid4()), key, self.owner, seq, text,
                    json.dumps(vector).encode(), json.dumps({'model': model, 'rule_id': 'doc-source-clean'})))

    def list(self):
        with closing(self.db.connect()) as conn:
            return [dict(row) for row in conn.execute(
                f'SELECT {METADATA} FROM documents WHERE owner_id=? AND deleted_at IS NULL ORDER BY created_at DESC,id',
                (self.owner,))]

    def get(self, key, ready=False):
        with closing(self.db.connect()) as conn:
            row = conn.execute(f'SELECT {METADATA} FROM documents WHERE id=? AND owner_id=? AND deleted_at IS NULL',
                               (key, self.owner)).fetchone()
        if not row or ready and row['status'] != 'ready':
            raise HTTPException(404, 'DOCUMENT_UNAVAILABLE')
        return dict(row)

    def chunks(self, key):
        with closing(self.db.connect()) as conn:
            return [dict(row) for row in conn.execute("""SELECT c.* FROM doc_chunks c
                JOIN documents d ON d.id=c.document_id AND d.owner_id=c.owner_id
                WHERE c.document_id=? AND c.owner_id=? AND d.owner_id=?
                AND d.deleted_at IS NULL AND d.status='ready' ORDER BY c.seq""", (key, self.owner, self.owner))]

    def delete(self, key):
        with transaction(self.db) as conn:
            if not conn.execute("""UPDATE documents SET deleted_at=? WHERE id=? AND owner_id=?
                    AND deleted_at IS NULL""", (now(), key, self.owner)).rowcount:
                raise HTTPException(404, 'DOCUMENT_UNAVAILABLE')
            conn.execute('DELETE FROM doc_chunks WHERE document_id=? AND owner_id=?', (key, self.owner))
