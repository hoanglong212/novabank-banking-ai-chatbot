"""Create a NEW reproducible synthetic banking dataset, never reseed a database.

Business IDs/dates/values are deterministic. Password salts and operational
security material remain random and are deliberately excluded from its hash.
"""
import argparse
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
from types import SimpleNamespace
import sys
import uuid as uuidlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
ANCHOR = date(2026, 11, 15)
MONTHS = tuple(date(2026, month, 1) for month in range(6, 12))
START = '2026-06-01T01:00:00+00:00'
SURNAMES = ('Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Vũ', 'Đặng', 'Bùi', 'Đỗ', 'Hồ')
GIVEN = ('Minh An', 'Khánh Bình', 'Ngọc Châu', 'Thu Dung', 'Gia Hân', 'Quang Huy', 'Bảo Khang', 'Mai Linh', 'Thanh Nam', 'Phương Thảo')
ROLES = ('support', 'operations', 'auditor', 'admin')


@contextmanager
def seed_context(value):
    from app import database, products, posting, ledger, action_security
    modules = (database, products, posting, ledger, action_security)
    old_uuid = [(module, getattr(module, 'uuid')) for module in modules if hasattr(module, 'uuid')]
    original = database.now, database.SEED_ACCOUNTS, database.SEED_TRANSACTIONS
    counter = 0
    def next_id():
        nonlocal counter
        counter += 1
        return uuidlib.uuid5(uuidlib.NAMESPACE_URL, f'novabank-synthetic:{value}:{counter}')
    try:
        for module, _ in old_uuid:
            module.uuid = SimpleNamespace(uuid4=next_id)
        # Start with coherent zero-balance accounts. Do not retain the seven
        # legacy display-only transactions from the small built-in demo.
        database.now = lambda: START
        database.SEED_ACCOUNTS, database.SEED_TRANSACTIONS = [], []
        yield
    finally:
        database.now, database.SEED_ACCOUNTS, database.SEED_TRANSACTIONS = original
        for module, old in old_uuid:
            module.uuid = old


def _fingerprint(conn):
    columns = {
        'users': 'id,name,email,role,status,auth_version,created_at',
        'accounts': 'id,owner_id,holder_name,balance_vnd,status',
        'transfers': 'id,owner_id,from_account,to_account,amount_vnd,status,created_at',
        'account_labels': '*', 'beneficiaries': '*', 'transactions': '*',
        'ledger_accounts': '*', 'ledger_entries': '*', 'cards': '*',
        'card_transactions': '*', 'bills': '*', 'savings': '*', 'savings_events': '*',
        'savings_goals': '*', 'budgets': '*', 'support_tickets': '*', 'ticket_messages': '*',
        'ticket_assignments': '*', 'product_transaction_details': '*', 'transaction_categories': '*',
    }
    digest = hashlib.sha256()
    for table, projection in columns.items():
        digest.update(table.encode())
        rows = [tuple(row) for row in conn.execute('SELECT ' + projection + ' FROM ' + table)]
        digest.update(json.dumps(sorted(rows), ensure_ascii=False, separators=(',', ':')).encode())
    return digest.hexdigest()


def _identities(conn):
    from app.identity import hash_password
    from app.faq import fold
    owners = ['alice', 'bob', 'charlie', *[f'cust{i:03}' for i in range(1, 48)]]
    for index, owner in enumerate(owners):
        name = SURNAMES[index % len(SURNAMES)] + ' ' + GIVEN[(index // len(SURNAMES) + index) % len(GIVEN)]
        if index < 3:
            conn.execute('UPDATE users SET name=?,created_at=? WHERE id=?', (name, START, owner))
        else:
            # No predictable fixture passwords or deterministic security salts.
            conn.execute('''INSERT INTO users(id,name,email,password_hash,role,status,auth_version,created_at)
                VALUES (?,?,?,?,'customer','ACTIVE',0,?)''',
                (owner, name, owner + '@novabank.test', hash_password(secrets.token_urlsafe(24)), START))
        conn.execute("INSERT INTO customer_profiles(user_id,phone,phone_verified_at,kyc_status) VALUES (?,'',NULL,'VERIFIED') ON CONFLICT(user_id) DO UPDATE SET kyc_status='VERIFIED'", (owner,))
        for number in range(1, 3 + index % 2):
            account = f'ACC-{owner.upper()}-{number:03}'
            conn.execute("INSERT INTO accounts(id,owner_id,holder_name,balance_vnd,status) VALUES (?,?,?,0,'ACTIVE')", (account, owner, fold(name).upper()))
            conn.execute("INSERT INTO ledger_accounts(id,customer_account_id,kind) VALUES (?,?,'CUSTOMER')", (account, account))
            label = ('Chi tiêu hằng ngày', 'Quỹ gia đình', 'Khoản dự phòng')[number - 1]
            conn.execute('INSERT INTO account_labels(account_id,nickname) VALUES (?,?)', (account, label))
    for role in ROLES:
        conn.execute('UPDATE users SET created_at=? WHERE id=?', (START, role))
        for number in (2, 3):
            user = f'{role}_{number:02}'
            name = f'{SURNAMES[number]} {GIVEN[(number + len(role)) % len(GIVEN)]}'
            conn.execute('''INSERT INTO users(id,name,email,password_hash,role,status,auth_version,created_at)
                VALUES (?,?,?,?,?,'ACTIVE',0,?)''',
                (user, name, user + '@novabank.test', hash_password(secrets.token_urlsafe(24)), role, START))
    return owners


def _stamp(month, day):
    return month.replace(day=day).isoformat() + 'T02:00:00+00:00'


def _activity(conn, user, index, rng):
    from app import products
    from app.banking_schema import ensure_products
    ensure_products(conn, user.id, START)
    accounts = [row[0] for row in conn.execute('SELECT id FROM accounts WHERE owner_id=? ORDER BY id', (user.id,))]
    # Preserve two empty reserve accounts for zero-balance boundary tests.
    if index == 49:
        accounts = accounts[:1]
    primary = accounts[0]
    for month_index, month in enumerate(MONTHS):
        for account_number, account in enumerate(accounts):
            income = 8000000 + index * 25000 + rng.randrange(15) * 100000
            journal = f'SYN:{user.id}:{account_number}:{month_index}:income'
            products.money(conn, user, account, income, True, 'SYS-CLEARING', journal, 'DEMO_INCOME', '', 'Mô phỏng — Lương Công ty Sen Xanh', _stamp(month, 1))
        for day, category, label, base in ((3, 'food', 'Ăn uống Cửa hàng Lá Sen', 220000),
                (6, 'transport', 'Đi lại Xe Xanh', 130000), (9, 'shopping', 'Mua sắm Chợ Bình An', 620000)):
            for account_number, account in enumerate(accounts):
                amount = base + rng.randrange(20) * 10000
                journal = f'SYN:{user.id}:{account_number}:{month_index}:{category}'
                tx = products.money(conn, user, account, amount, False, 'SYS-MERCHANTS', journal, 'DEMO_PURCHASE', '', 'Mô phỏng — ' + label, _stamp(month, day))
                conn.execute('INSERT INTO transaction_categories(transaction_id,category) VALUES (?,?)', (tx, category))
        credit = 'CARD-' + user.id + '-CREDIT'
        seconds = int(datetime.fromisoformat(_stamp(month, 10)).timestamp())
        products.execute(conn, user, 'CARD_PURCHASE', {'resource_id': credit, 'amount_vnd': 200000 + index * 1000, 'label': 'Mô phỏng — Nhà sách Sen Xanh'}, f'SYN:{user.id}:{month_index}:credit', seconds)
        for account_number, account in enumerate(accounts):
            journal = f'SYN:{user.id}:{account_number}:{month_index}:internet'
            tx = products.money(conn, user, account, 250000, False, 'SYS-MERCHANTS', journal, 'DEMO_PURCHASE', '', 'Mô phỏng — Internet gia đình', _stamp(month, 12))
            conn.execute('INSERT INTO transaction_categories(transaction_id,category) VALUES (?,?)', (tx, 'internet'))
        if month_index == 2:
            seconds = int(datetime.fromisoformat(_stamp(month, 13)).timestamp())
            products.execute(conn, user, 'OPEN_SAVINGS', {'account_id': primary, 'amount_vnd': 3000000,
                'term_months': (3, 6, 12)[index % 3], 'label': 'Mô phỏng — Quỹ dự phòng gia đình'}, f'SYN:{user.id}:saving', seconds)
        seconds = int(datetime.fromisoformat(_stamp(month, 14)).timestamp())
        products.execute(conn, user, 'REPAY_CARD', {'resource_id': credit, 'amount_vnd': 100000,
            'label': 'Mô phỏng — Trả nợ thẻ định kỳ'}, f'SYN:{user.id}:{month_index}:repay', seconds)
    seconds = int(datetime.fromisoformat(_stamp(MONTHS[-1], 15)).timestamp())
    products.execute(conn, user, 'PAY_BILL', {'resource_id': 'BILL-' + user.id + '-electricity',
        'account_id': primary}, f'SYN:{user.id}:bill-electricity', seconds)


def _services(conn, owners):
    from datetime import timedelta
    for index, owner in enumerate(owners):
        for offset in (1, 2, 3):
            target = owners[(index + offset) % len(owners)]
            account = conn.execute('SELECT id,holder_name FROM accounts WHERE owner_id=? ORDER BY id LIMIT 1', (target,)).fetchone()
            conn.execute('INSERT INTO beneficiaries VALUES (?,?,?,?,?,?,?,?)',
                (f'BEN-SYN-{owner}-{offset}', owner, account[0], 'NovaBank', account[1], f'Người nhận mô phỏng {offset}', 'untrusted', START))
        conn.execute('UPDATE bills SET due_date=?,saved=1 WHERE owner_id=?', ((ANCHOR + timedelta(days=7 if index % 4 else -3)).isoformat(), owner))
        saving = conn.execute('SELECT id FROM savings WHERE owner_id=?', (owner,)).fetchone()[0]
        conn.execute('INSERT INTO savings_goals(id,owner_id,label,target_vnd,target_date,savings_id) VALUES (?,?,?,?,?,?)', (f'GOAL-SYN-{owner}', owner, 'Mô phỏng — Kế hoạch gia đình', 5000000, '2027-06-01', saving))
        conn.execute('INSERT INTO budgets VALUES (?,?,?,?)', (owner, ANCHOR.strftime('%Y-%m'), 'shopping', 1800000 + index * 10000))
        for number, subject in ((1, 'Hỏi về biên lai giao dịch mô phỏng'), (2, 'Kiểm tra giao thẻ mô phỏng')):
            ticket = f'TKT-SYN-{owner.upper()}-{number}'
            status = 'OPEN' if number == 1 else 'RESOLVED'
            conn.execute('INSERT INTO support_tickets(id,owner_id,subject,description,status,created_at) VALUES (?,?,?,?,?,?)',
                (ticket, owner, subject, 'Đây là yêu cầu hỗ trợ trong dữ liệu mô phỏng, không chứa dữ liệu khách hàng thật.', status, '2026-11-10T02:00:00+00:00'))
            staff = 'support' if index % 3 == 0 else f'support_{2 + index % 2:02}'
            conn.execute('INSERT INTO ticket_assignments VALUES (?,?,?)', (ticket, staff, 'GENERAL'))
            conn.execute('INSERT INTO ticket_messages VALUES (?,?,?,?,?)', (f'MSG-SYN-{owner}-{number}', ticket, staff, 'Nhân viên đã ghi nhận yêu cầu mô phỏng và đang kiểm tra thông tin.', '2026-11-11T02:00:00+00:00'))


def seed(target, seed=20261115):
    from app.database import Database
    from app.identity import lookup_principal, transaction
    from app.ledger import reconcile
    if type(seed) is not int or not 0 <= seed < 2 ** 63:
        raise ValueError('Seed must be a nonnegative 63-bit integer.')
    if Path(target).is_symlink():
        raise ValueError('Choose a new path; existing symbolic links are never followed.')
    target = Path(target).resolve()
    report_path = target.with_suffix('.seed.json')
    artifacts = (target, report_path, Path(str(target) + '.mfa.key'), Path(str(target) + '-wal'), Path(str(target) + '-shm'))
    if any(path.exists() or path.is_symlink() for path in artifacts):
        raise ValueError('Choose a new path; existing databases, reports and sidecars are never overwritten.')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Choose a new path; existing databases are never overwritten.')
    os.close(descriptor)
    rng = random.Random(seed)
    with seed_context(seed):
        db = Database(str(target))
        db.initialize()  # Apply every currently registered migration; no maximum version assumption.
        with transaction(db) as conn:
            owners = _identities(conn)
        for index, owner in enumerate(owners):
            user = lookup_principal(db, owner)
            with transaction(db) as conn:
                _activity(conn, user, index, rng)
        with transaction(db) as conn:
            _services(conn, owners)
            conn.execute("""INSERT INTO transfers
                (id,owner_id,from_account,to_bank,to_account,to_name,internal,amount_vnd,content,status,created_at)
                VALUES ('TR-SYN-PENDING','alice','ACC-ALICE-001','NovaBank','ACC-BOB-001','SYNTHETIC RECIPIENT',1,1000,
                'Synthetic pending draft; no ledger posting','PENDING_OTP',?)""", (START,))
        reconciled = reconcile(db)
        if not reconciled['balanced']:
            raise RuntimeError('Synthetic seed ledger failed reconciliation; target preserved for diagnosis.')
        with db.connect() as conn:
            tables = ('users', 'accounts', 'transactions', 'ledger_entries', 'beneficiaries', 'cards', 'card_transactions', 'bills', 'savings', 'savings_goals', 'support_tickets')
            counts = {table: conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in tables}
            if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or conn.execute('PRAGMA foreign_key_check').fetchall():
                raise RuntimeError('Synthetic seed integrity check failed.')
            report = {'synthetic': True, 'seed': seed, 'anchor_date': ANCHOR.isoformat(), 'customers': len(owners),
                'months': [month.strftime('%Y-%m') for month in MONTHS], 'counts': counts,
                'staff_per_role': 3, 'ledger_balanced': True, 'business_fingerprint': _fingerprint(conn),
                'note': 'Fictional names and reserved .test email addresses. Security salts are random; existing Alice/Bob/Charlie demo logins are retained. No legacy display-only history.'}
        with report_path.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--seed', '--seedvalue', type=int, default=20261115)
    options = parser.parse_args()
    print(json.dumps(seed(options.output, options.seed), indent=2))
