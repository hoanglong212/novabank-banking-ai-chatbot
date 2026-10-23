"""Atomic, internal simulated payments. Never exposed as an agent write tool."""
import time
import uuid
from fastapi import HTTPException
from .database import now


def initialize_banking(db):
    with db.connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS bank_accounts (
          id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, owner_name TEXT NOT NULL,
          balance_vnd INTEGER NOT NULL CHECK(balance_vnd>=0),
          currency TEXT NOT NULL DEFAULT 'VND', active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS transfer_intents (
          id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
          source_account_id TEXT NOT NULL REFERENCES bank_accounts(id),
          recipient_account_id TEXT NOT NULL REFERENCES bank_accounts(id),
          amount_vnd INTEGER NOT NULL CHECK(amount_vnd>0 AND amount_vnd<=1000000000000),
          description TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','completed','cancelled')),
          expires_at INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bank_transactions (
          id TEXT PRIMARY KEY, source_account_id TEXT NOT NULL REFERENCES bank_accounts(id),
          recipient_account_id TEXT REFERENCES bank_accounts(id), amount_vnd INTEGER NOT NULL CHECK(amount_vnd>0),
          description TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
          intent_id TEXT UNIQUE REFERENCES transfer_intents(id));
        CREATE TABLE IF NOT EXISTS banking_events (
          id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, intent_id TEXT NOT NULL,
          event TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_bank_transactions_source ON bank_transactions(source_account_id);
        CREATE INDEX IF NOT EXISTS idx_bank_transactions_recipient ON bank_transactions(recipient_account_id);
        ''')
        conn.executemany('INSERT OR IGNORE INTO bank_accounts(id,owner_id,owner_name,balance_vnd) VALUES (?,?,?,?)',[
            ('ACC-ALICE-001','alice','Alice',12500000),('ACC-BOB-001','bob','Bob',8750000)])
        for tid, account, amount, status in [('TX-1001','ACC-ALICE-001',300000,'COMPLETED'),
                                             ('TX-1002','ACC-ALICE-001',950000,'PENDING'),
                                             ('TX-2001','ACC-BOB-001',200000,'COMPLETED')]:
            conn.execute('''INSERT OR IGNORE INTO bank_transactions
                (id,source_account_id,amount_vnd,description,status,created_at) VALUES (?,?,?,?,?,?)''',
                (tid,account,amount,'Historical demo transaction',status,now()))


def accounts_for(db,owner):
    with db.connect() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM bank_accounts WHERE owner_id=? AND active=1 ORDER BY id',(owner,))]


def transactions_for(db,owner,transaction_id=None):
    with db.connect() as conn:
        query = '''SELECT t.* FROM bank_transactions t
          JOIN bank_accounts s ON s.id=t.source_account_id
          LEFT JOIN bank_accounts r ON r.id=t.recipient_account_id
          WHERE (s.owner_id=? OR r.owner_id=?)'''
        params = [owner,owner]
        if transaction_id:
            query += ' AND t.id=?'
            params.append(transaction_id)
        query += ' ORDER BY t.created_at DESC,t.rowid DESC LIMIT 100'
        return [dict(row) for row in conn.execute(query,params)]


def get_intent(db,owner,intent_id):
    with db.connect() as conn:
        row = conn.execute('''SELECT i.*,a.owner_name AS recipient_name FROM transfer_intents i
          JOIN bank_accounts a ON a.id=i.recipient_account_id WHERE i.id=? AND i.owner_id=?''',(intent_id,owner)).fetchone()
        if not row:
            raise HTTPException(404,'Transfer preview not found')
        return dict(row)


def create_intent(db,owner,source,recipient,amount,description):
    if source==recipient:
        raise HTTPException(422,'Choose a different recipient account')
    identifier = 'INT-'+uuid.uuid4().hex.upper()
    with db.connect() as conn:
        sender = conn.execute('SELECT * FROM bank_accounts WHERE id=? AND owner_id=? AND active=1',(source,owner)).fetchone()
        receiver = conn.execute('SELECT * FROM bank_accounts WHERE id=? AND active=1',(recipient,)).fetchone()
        if not sender or not receiver:
            raise HTTPException(404,'Account unavailable')
        if sender['balance_vnd'] < amount:
            raise HTTPException(409,'Insufficient funds')
        conn.execute('''INSERT INTO transfer_intents VALUES (?,?,?,?,?,?, 'pending',?,?)''',
                     (identifier,owner,source,recipient,amount,description,int(time.time())+300,now()))
    return get_intent(db,owner,identifier)


def confirm_transfer(db,owner,intent_id):
    with db.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        intent = conn.execute('SELECT * FROM transfer_intents WHERE id=? AND owner_id=?',(intent_id,owner)).fetchone()
        if not intent:
            raise HTTPException(404,'Transfer preview not found')
        if intent['status']=='completed':
            row = conn.execute('SELECT * FROM bank_transactions WHERE intent_id=?',(intent_id,)).fetchone()
            if not row:
                raise HTTPException(409,'Transfer state is inconsistent')
            return dict(row)
        if intent['status']!='pending' or intent['expires_at']<=int(time.time()):
            raise HTTPException(409,'Transfer preview expired or unavailable; create a new preview')
        recipient = conn.execute('SELECT id FROM bank_accounts WHERE id=? AND active=1',(intent['recipient_account_id'],)).fetchone()
        if not recipient:
            raise HTTPException(409,'Recipient unavailable')
        changed = conn.execute("UPDATE transfer_intents SET status='completed' WHERE id=? AND status='pending'",(intent_id,)).rowcount
        if changed!=1:
            raise HTTPException(409,'Transfer already processed')
        changed = conn.execute('''UPDATE bank_accounts SET balance_vnd=balance_vnd-?
          WHERE id=? AND owner_id=? AND active=1 AND balance_vnd>=?''',
          (intent['amount_vnd'],intent['source_account_id'],owner,intent['amount_vnd'])).rowcount
        if changed!=1:
            raise HTTPException(409,'Insufficient funds or source account unavailable')
        conn.execute('UPDATE bank_accounts SET balance_vnd=balance_vnd+? WHERE id=?',
                     (intent['amount_vnd'],intent['recipient_account_id']))
        transaction_id='TX-'+uuid.uuid4().hex.upper()
        conn.execute('''INSERT INTO bank_transactions VALUES (?,?,?,?,?,'COMPLETED',?,?)''',
                     (transaction_id,intent['source_account_id'],intent['recipient_account_id'],
                      intent['amount_vnd'],intent['description'],now(),intent_id))
        conn.execute('INSERT INTO banking_events VALUES (?,?,?,?,?)',
                     (uuid.uuid4().hex,owner,intent_id,'TRANSFER_COMPLETED',now()))
        return dict(conn.execute('SELECT * FROM bank_transactions WHERE id=?',(transaction_id,)).fetchone())
