"""Durable simulated interbank settlement; failure appends a compensating journal."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from .action_security import notify
from .database import now
from .identity import transaction
from .posting import audit, post_journal, business_day


def initialize_settlement(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=6').fetchone():
        return
    conn.execute('''CREATE TABLE transfer_quotes (transfer_id TEXT PRIMARY KEY REFERENCES transfers(id),
        fee_vnd INTEGER NOT NULL CHECK(typeof(fee_vnd)='integer' AND fee_vnd>=0))''')
    conn.execute('''CREATE TABLE interbank_settlements (transfer_id TEXT PRIMARY KEY REFERENCES transfers(id),
        status TEXT NOT NULL CHECK(status IN ('PENDING','COMPLETED','FAILED')), due_at TEXT NOT NULL,
        processed_at TEXT, failure_reason TEXT, reversal_transaction_id TEXT REFERENCES transactions(id))''')
    conn.execute('CREATE INDEX idx_settlement_due ON interbank_settlements(status,due_at)')
    conn.execute('INSERT INTO transfer_quotes SELECT id,0 FROM transfers')
    conn.execute('INSERT INTO schema_migrations VALUES (6,?)', (stamp,))


def fee(conn):
    return int(json.loads(conn.execute("SELECT value_json FROM bank_settings WHERE key='transfer_fee_vnd'").fetchone()[0]))


def enqueue(conn, transfer_id, stamp):
    due = (datetime.fromisoformat(stamp) + timedelta(seconds=5)).isoformat(timespec='seconds')
    conn.execute("INSERT INTO interbank_settlements VALUES (?,'PENDING',?,NULL,NULL,NULL)", (transfer_id, due))


def process_due(db, force=False):
    result = {'completed': 0, 'reversed': 0}
    with transaction(db) as conn:
        stamp = now()
        rows = conn.execute("SELECT s.*,t.*,q.fee_vnd FROM interbank_settlements s JOIN transfers t ON t.id=s.transfer_id "
                            "JOIN transfer_quotes q ON q.transfer_id=t.id WHERE s.status='PENDING' AND (s.due_at<=? OR ?)", (stamp, int(force))).fetchall()
        for row in rows:
            # Explicit, deterministic simulator scenario. Never contacts a real bank.
            failed = row['to_account'].endswith('0000')
            reversal = None
            if failed:
                amount = row['amount_vnd'] + row['fee_vnd']
                entries = [(row['from_account'], amount), ('SYS-CLEARING', -row['amount_vnd'])]
                if row['fee_vnd']:
                    entries.append(('SYS-FEES', -row['fee_vnd']))
                journal = 'REVERSAL:' + row['id']
                post_journal(conn, journal, entries, stamp, allow_frozen_credit=True)
                reversal = 'TX-' + uuid.uuid4().hex.upper()
                balance = conn.execute('SELECT balance_vnd FROM accounts WHERE id=?', (row['from_account'],)).fetchone()[0]
                conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)', (reversal, row['from_account'], amount, 'in', 'COMPLETED',
                             'Refund · simulated interbank rejection', business_day(stamp), stamp))
                conn.execute('INSERT INTO product_transaction_details VALUES (?,?,?,?,?,?,0)',
                             (reversal, journal, 'TRANSFER_REFUND', row['id'], balance, row['to_bank']))
                notify(conn, row['owner_id'], 'REFUND', 'Transfer refunded', f'{amount:,} VND returned, including the fee.', stamp, row['id'], reversal)
                result['reversed'] += 1
            else:
                result['completed'] += 1
                notify(conn, row['owner_id'], 'TRANSFER', 'Interbank transfer completed', f'{row["amount_vnd"]:,} VND delivered in the simulator.', stamp, row['id'], row['transaction_id'])
            status = 'FAILED' if failed else 'COMPLETED'
            conn.execute('UPDATE transactions SET status=? WHERE id=? AND status=\'PENDING\'', (status, row['transaction_id']))
            conn.execute('UPDATE interbank_settlements SET status=?,processed_at=?,failure_reason=?,reversal_transaction_id=? WHERE transfer_id=?',
                         (status, stamp, 'SIMULATED_RECIPIENT_REJECTED' if failed else None, reversal, row['id']))
            audit(conn, row['owner_id'], 'INTERBANK_' + status, row['id'], 'REVERSED' if failed else 'SETTLED', stamp)
            if not failed:
                from .insights import budgets_after_posting
                budgets_after_posting(conn, row['owner_id'], business_day(row['completed_at']))
    return result
