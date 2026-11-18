"""Read-only ledger/seed validation; optional cleanup only for a marked synthetic DB."""
import argparse
import json
from pathlib import Path
import sqlite3

def check(path, cleanup=False):
    path = Path(path).resolve(strict=True)
    if cleanup:
        marker = path.with_suffix('.seed.json')
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('synthetic') is not True:
            raise ValueError('Cleanup requires the seed generator synthetic manifest')
    with sqlite3.connect(path.as_uri() + ('?mode=rw' if cleanup else '?mode=ro'), uri=True) as conn:
        if cleanup:
            conn.execute('BEGIN EXCLUSIVE')
            # This is a legacy display-only pentest fixture. Never remove posted money.
            linked = conn.execute("SELECT 1 FROM product_transaction_details WHERE transaction_id='TX-PENTEST-E1'").fetchone()
            posted = conn.execute("SELECT 1 FROM transfers WHERE transaction_id='TX-PENTEST-E1'").fetchone()
            if linked or posted:
                raise ValueError('Refusing to remove a posted transaction')
            trigger = conn.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='completed_transactions_no_delete'").fetchone()
            if trigger:
                conn.execute('DROP TRIGGER completed_transactions_no_delete')
            conn.execute("DELETE FROM transactions WHERE id='TX-PENTEST-E1'")
            if trigger:
                conn.execute(trigger[0])
            # DDL and fixture deletion are atomic; a failure rolls the trigger back too.
        mismatches = conn.execute("""SELECT COUNT(*) FROM (
            SELECT a.id FROM accounts a LEFT JOIN ledger_accounts l ON l.customer_account_id=a.id
            LEFT JOIN ledger_entries e ON e.account_id=l.id GROUP BY a.id
            HAVING a.balance_vnd != COALESCE(SUM(e.amount_vnd),0) OR l.id IS NULL)""").fetchone()[0]
        unbalanced = conn.execute('SELECT COUNT(*) FROM (SELECT journal_id FROM ledger_entries GROUP BY journal_id HAVING SUM(amount_vnd)!=0 OR COUNT(*)<2)').fetchone()[0]
        negative = conn.execute('SELECT COUNT(*) FROM accounts WHERE balance_vnd<0').fetchone()[0]
        total = conn.execute('SELECT COALESCE(SUM(amount_vnd),0) FROM ledger_entries').fetchone()[0]
        return {'balanced':not(mismatches or unbalanced or negative or total),
                'mismatched_accounts':mismatches,'unbalanced_journals':unbalanced,'negative_accounts':negative,
                'ledger_total_vnd':total,'counts':{table:conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                    for table in ('users','accounts','transactions')},
                'zero_balance_accounts':conn.execute('SELECT COUNT(*) FROM accounts WHERE balance_vnd=0').fetchone()[0],
                'pending_drafts':conn.execute("SELECT COUNT(*) FROM transfers WHERE status='PENDING_OTP'").fetchone()[0],
                'pentest_fixture_rows':conn.execute("SELECT COUNT(*) FROM transactions WHERE id='TX-PENTEST-E1'").fetchone()[0]}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database',type=Path)
    parser.add_argument('--cleanup-pentest-fixture',action='store_true')
    args=parser.parse_args()
    result=check(args.database,args.cleanup_pentest_fixture)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['balanced'] else 1)
