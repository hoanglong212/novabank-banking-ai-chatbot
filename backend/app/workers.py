"""Small persistent-job worker; no extra service/dependency required."""
import asyncio
import logging
from .config import setting
from .database import now
from .identity import transaction
from .action_security import notify
from .ledger import reconcile
from .settlement import process_due

log = logging.getLogger('novabank.worker')


def maintenance(db):
    settled = process_due(db)
    today = now()[:10]
    with db.connect() as conn:
        latest = conn.execute('SELECT created_at FROM reconciliation_runs ORDER BY rowid DESC LIMIT 1').fetchone()
    if not latest or latest[0][:10] != today:
        result = reconcile(db)
        if not result['balanced']:
            with transaction(db) as conn:
                for row in conn.execute("SELECT id FROM users WHERE role IN ('admin','operations') AND status='ACTIVE'").fetchall():
                    notify(conn, row[0], 'RECONCILIATION', 'Ledger reconciliation requires attention',
                           'Open Operations and review the mismatch report.', now(), result['id'], dedupe='reconcile:' + result['id'] + ':' + row[0])
    with transaction(db) as conn:
        for row in conn.execute("SELECT * FROM bills WHERE status='UNPAID' AND saved=1 AND due_date<=date(?,'+3 days')", (today,)).fetchall():
            notify(conn, row['owner_id'], 'BILL', 'Bill due soon', f'{row["provider"]}: {row["amount_vnd"]:,} VND due {row["due_date"]}.', now(), row['id'], dedupe='bill-due:' + row['id'])
        conn.execute('UPDATE dev_outbox SET secret_text=NULL,action_path=NULL WHERE expires_at IS NOT NULL AND expires_at<=unixepoch()')
        conn.execute("UPDATE action_challenges SET payload_json='{}',otp_hash='' WHERE expires_at<=unixepoch() AND consumed_at IS NULL")
        conn.execute("UPDATE agent_runs SET status='EXPIRED',bound_request_json='{}',vault_json='{}' WHERE expires_at<=unixepoch() AND status IN ('READY','RUNNING')")
    return settled


async def loop(db):
    while True:
        try:
            await asyncio.to_thread(maintenance, db)
        except Exception:
            log.exception('bank_worker_failed')
        await asyncio.sleep(2)
