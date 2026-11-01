"""Create a NEW rich synthetic demo database. Never modifies an existing target."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def seed(target):
    if target.exists():
        raise ValueError('Choose a new database path; existing databases are never reseeded.')
    from app import database, products
    from app.banking_schema import ensure_products
    from app.identity import hash_password, lookup_principal, transaction
    from app.ledger import reconcile
    today = date.today()
    months = []
    for back in range(5, -1, -1):
        index = today.year * 12 + today.month - 1 - back
        months.append(date(index // 12, index % 12 + 1, 1))
    original_now = database.now
    database.now = lambda: months[0].isoformat() + 'T00:00:00+00:00'
    db = database.Database(str(target))
    try: db.initialize()
    finally: database.now = original_now
    with transaction(db) as conn:
        for name in ('dana', 'emma'):
            conn.execute("INSERT INTO users VALUES (?,?,?,?, 'customer','ACTIVE',0,?)",
                (name, name.title() + ' Nguyen', name + '@novabank.test', hash_password(name.title() + '@2026'), database.now()))
            account = 'ACC-' + name.upper() + '-001'
            conn.execute("INSERT INTO accounts(id,owner_id,holder_name,balance_vnd,status) VALUES (?,?,?,0,'ACTIVE')", (account, name, name.title() + ' Nguyen'))
            conn.execute("INSERT INTO ledger_accounts VALUES (?,?,'CUSTOMER')", (account, account))
    for owner in ('alice', 'bob', 'charlie', 'dana', 'emma'):
        user = lookup_principal(db, owner); account = user.accounts[0]
        with transaction(db) as conn:
            ensure_products(conn, owner, database.now())
            for i, month in enumerate(months):
                stamp = month.isoformat() + 'T01:00:00+00:00'
                products.money(conn, user, account, 12000000 + i*100000, True, 'SYS-CLEARING', 'DEMO-SALARY-' + uuid.uuid4().hex, 'DEMO_INCOME', '', 'Salary · synthetic demo', stamp)
                for ordinal, (category, label, amount) in enumerate([('food','Coffee and food',345000),('transport','Taxi trips',420000),('shopping','Grocery market',1800000),('internet','Internet service',250000)]):
                    day = min(3 + ordinal * 6, today.day) if i == 5 else 3 + ordinal * 6
                    spent_at = month.replace(day=day).isoformat() + 'T02:00:00+00:00'
                    tx = products.money(conn, user, account, amount + i*10000, False, 'SYS-MERCHANTS', 'DEMO-SPEND-' + uuid.uuid4().hex, 'DEMO_PURCHASE', '', label, spent_at)
                    conn.execute('INSERT INTO transaction_categories VALUES (?,?)', (tx, category))
            seconds = int(datetime.now(timezone.utc).timestamp())
            products.execute(conn, user, 'OPEN_SAVINGS', {'account_id': account, 'amount_vnd': 3000000, 'term_months': 6, 'label': 'Emergency reserve'}, 'DEMO-SAVE-' + uuid.uuid4().hex, seconds)
            products.execute(conn, user, 'CARD_PURCHASE', {'resource_id': 'CARD-' + owner + '-CREDIT', 'amount_vnd': 450000, 'label': 'Book store'}, 'DEMO-CREDIT-' + uuid.uuid4().hex, seconds)
            conn.execute('INSERT INTO budgets VALUES (?,?,?,?)', (owner, today.strftime('%Y-%m'), 'shopping', 2000000))
            conn.execute('INSERT INTO beneficiaries VALUES (?,?,?,?,?,?,?,?)', ('BEN-' + owner, owner, 'ACC-BOB-001' if owner != 'bob' else 'ACC-ALICE-001', 'NovaBank', 'Bob Tran' if owner != 'bob' else 'Alice Nguyen', 'Family', 'untrusted', database.now()))
    report = reconcile(db)
    if not report['balanced']: raise RuntimeError('Seed ledger mismatch')
    with db.connect() as conn:
        counts = {t: conn.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in ('users','accounts','transactions','ledger_entries','cards','bills','savings')}
    result = {'db': str(target), 'months': [m.strftime('%Y-%m') for m in months], 'customers': 5, 'counts': counts, 'ledger_balanced': True,
              'note': 'Synthetic fixture. Seven retained legacy display transactions predate ledger evidence.'}
    target.with_suffix('.seed.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', required=True, type=Path)
    print(json.dumps(seed(p.parse_args().out.resolve()), indent=2))
