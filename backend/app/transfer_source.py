"""Persistent origin hints; origin never grants authority or recipient trust."""


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=20').fetchone():
        return
    conn.execute('''CREATE TABLE transfer_sources (transfer_id TEXT PRIMARY KEY REFERENCES transfers(id),
        origin TEXT NOT NULL CHECK(origin IN ('manual','qr','ocr')))''')
    conn.execute('INSERT INTO schema_migrations VALUES (20,?)', (stamp,))


def origin(conn, transfer_id):
    row = conn.execute('SELECT origin FROM transfer_sources WHERE transfer_id=?', (transfer_id,)).fetchone()
    return row[0] if row else 'manual'
