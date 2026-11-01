"""Owner-scoped spending, budgets and bounded downloadable statements."""
import calendar
import csv
from datetime import date, datetime, time, timedelta, timezone
from html import escape
from io import BytesIO, StringIO
from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
from . import receipts  # Registers the bundled Unicode font.
from .action_security import notify
from .database import now
from .identity import transaction

CATEGORIES = ('food', 'transport', 'shopping', 'electricity', 'water', 'internet', 'mobile', 'transfer', 'other')


def month_bounds(month):
    try:
        start = date.fromisoformat(month + '-01')
        end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
        return start.isoformat(), end.isoformat()
    except ValueError:
        raise HTTPException(422, 'Use a valid month in YYYY-MM format.')


def category(row):
    if row.get('category'):
        return row['category']
    text = row['description'].lower()
    for name, words in {'food': ('coffee', 'food', 'restaurant', 'cafe'),
                        'transport': ('ride', 'taxi', 'bus', 'fuel'),
                        'shopping': ('shop', 'store', 'market'),
                        'transfer': ('transfer',)}.items():
        if any(word in text for word in words):
            return name
    return 'other'


def month_data(conn, owner, month):
    start, end = month_bounds(month)
    rows = [dict(r) for r in conn.execute('''SELECT t.*,c.category,p.kind,COALESCE(d.fee_vnd,0) AS fee_vnd FROM transactions t
        JOIN accounts a ON a.id=t.account_id LEFT JOIN transaction_categories c ON c.transaction_id=t.id
        LEFT JOIN product_transaction_details p ON p.transaction_id=t.id
        LEFT JOIN transaction_details d ON d.transaction_id=t.id
        WHERE a.owner_id=? AND t.date BETWEEN ? AND ? AND t.status='COMPLETED' ''', (owner, start, end))]
    # Moving principal between payment/savings and paying a credit balance are not new spending.
    rows = [r for r in rows if r['kind'] not in ('OPEN_SAVINGS', 'WITHDRAW_SAVINGS', 'REPAY_CARD', 'TRANSFER_REFUND')]
    # Savings interest is new income; only principal movement is excluded.
    interest = conn.execute('''SELECT -e.amount_vnd AS amount_vnd,t.date FROM transactions t
        JOIN accounts a ON a.id=t.account_id JOIN product_transaction_details p ON p.transaction_id=t.id
        JOIN ledger_entries e ON e.journal_id=p.journal_id AND e.account_id='SYS-INTEREST'
        WHERE a.owner_id=? AND t.date BETWEEN ? AND ? AND t.status='COMPLETED' AND p.kind='WITHDRAW_SAVINGS' ''', (owner, start, end))
    rows.extend(dict(amount_vnd=r['amount_vnd'], direction='in', description='Savings interest', date=r['date'], category=None) for r in interest)
    credit = conn.execute('''SELECT ct.*,substr(ct.created_at,1,10) AS date FROM card_transactions ct
        JOIN cards c ON c.id=ct.card_id WHERE c.owner_id=? AND c.kind='CREDIT'
        AND ct.kind='CARD_PURCHASE' AND substr(ct.created_at,1,10) BETWEEN ? AND ?''', (owner, start, end))
    rows.extend(dict(amount_vnd=r['amount_vnd'], direction='out', description=r['merchant'], date=r['date'], category=None) for r in credit)
    totals = {name: 0 for name in CATEGORIES}
    daily = {}
    income = expense = 0
    for row in rows:
        if row['direction'] == 'in':
            income += row['amount_vnd']
        else:
            amount = row['amount_vnd'] + row.get('fee_vnd', 0)
            expense += amount
            totals[category(row)] += amount
            daily[row['date']] = daily.get(row['date'], 0) + amount
    return {'month': month, 'income_vnd': income, 'expense_vnd': expense, 'net_vnd': income - expense,
            'categories': [{'category': k, 'amount_vnd': v} for k, v in totals.items()],
            'daily': [{'date': k, 'amount_vnd': v} for k, v in sorted(daily.items())]}


def evaluate_budgets(conn, owner, data):
    spent = {r['category']: r['amount_vnd'] for r in data['categories']}
    result = []
    for row in conn.execute('SELECT * FROM budgets WHERE owner_id=? AND month=?', (owner, data['month'])).fetchall():
        item = dict(row); item['spent_vnd'] = spent[item['category']]
        item['exceeded'] = item['spent_vnd'] >= item['amount_vnd']
        result.append(item)
        if item['exceeded']:
            notify(conn, owner, 'BUDGET', 'Budget reached', f'Your {item["category"]} spending reached its {data["month"]} budget.',
                   now(), dedupe=f'budget:{owner}:{data["month"]}:{item["category"]}')
    return result


def budgets_after_posting(conn, owner, day):
    month = day[:7]
    if conn.execute('SELECT 1 FROM budgets WHERE owner_id=? AND month=? LIMIT 1', (owner, month)).fetchone():
        evaluate_budgets(conn, owner, month_data(conn, owner, month))


def summary(db, user, month):
    with transaction(db) as conn:
        from .banking_schema import ensure_products
        ensure_products(conn, user.id, now())
        data = month_data(conn, user.id, month)
        data['budgets'] = evaluate_budgets(conn, user.id, data)
        year, m = map(int, month.split('-'))
        previous = f'{year if m > 1 else year-1:04d}-{m-1 if m > 1 else 12:02d}'
        data['previous'] = month_data(conn, user.id, previous)
        data['total_balance_vnd'] = conn.execute('SELECT COALESCE(SUM(balance_vnd),0) FROM accounts WHERE owner_id=?', (user.id,)).fetchone()[0]
        data['savings_principal_vnd'] = conn.execute("SELECT COALESCE(SUM(principal_vnd),0) FROM savings WHERE owner_id=? AND status='ACTIVE'", (user.id,)).fetchone()[0]
        data['credit_debt_vnd'] = conn.execute("SELECT COALESCE(SUM(outstanding_vnd),0) FROM cards WHERE owner_id=?", (user.id,)).fetchone()[0]
        data['unpaid_bills'] = conn.execute("SELECT COUNT(*) FROM bills WHERE owner_id=? AND status='UNPAID'", (user.id,)).fetchone()[0]
        return data


def set_budget(db, user, month, cat, amount):
    month_bounds(month)
    if cat not in CATEGORIES:
        raise HTTPException(422, 'Unsupported category.')
    with transaction(db) as conn:
        conn.execute('INSERT INTO budgets VALUES (?,?,?,?) ON CONFLICT(owner_id,month,category) DO UPDATE SET amount_vnd=excluded.amount_vnd', (user.id, month, cat, amount))
        evaluate_budgets(conn, user.id, month_data(conn, user.id, month))
    return {'message': 'Budget saved.'}


def statement_totals(conn, owner, start, end):
    from .posting import VIETNAM, business_day
    lower = datetime.combine(start, time.min, VIETNAM).astimezone(timezone.utc).isoformat(timespec='seconds')
    upper = datetime.combine(end + timedelta(days=1), time.min, VIETNAM).astimezone(timezone.utc).isoformat(timespec='seconds')
    migration = conn.execute('SELECT applied_at FROM schema_migrations WHERE version=1').fetchone()[0]
    boundary = business_day(migration)
    totals = []
    for account in conn.execute('SELECT id FROM accounts WHERE owner_id=? ORDER BY id', (owner,)).fetchall():
        # Imported equity is an opening balance, never income. Earlier legacy history
        # cannot reconstruct an authoritative pre-migration balance.
        opening, credit, debit = conn.execute('''SELECT
            COALESCE(SUM(CASE WHEN journal_id LIKE 'OPENING:%' OR created_at<? THEN amount_vnd ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN journal_id NOT LIKE 'OPENING:%' AND created_at>=? AND created_at<? AND amount_vnd>0 THEN amount_vnd ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN journal_id NOT LIKE 'OPENING:%' AND created_at>=? AND created_at<? AND amount_vnd<0 THEN -amount_vnd ELSE 0 END),0)
            FROM ledger_entries WHERE account_id=?''', (lower, lower, upper, lower, upper, account['id'])).fetchone()
        closing = opening + credit - debit
        totals.append([account['id'], opening if start.isoformat() >= boundary else None,
                       credit, debit, closing if end.isoformat() >= boundary else None])
    return totals, boundary


def statement(db, user, start, end, fmt):
    if start > end or (end - start).days > 366:
        raise HTTPException(400, 'Choose an ordered period of at most one year.')
    with db.connect() as conn:
        conn.execute('BEGIN')
        rows = [dict(r) for r in conn.execute('''SELECT t.*,p.balance_after_vnd AS product_balance,d.balance_after_vnd,COALESCE(d.fee_vnd,0) AS fee_vnd
            FROM transactions t JOIN accounts a ON a.id=t.account_id
            LEFT JOIN transaction_details d ON d.transaction_id=t.id
            LEFT JOIN product_transaction_details p ON p.transaction_id=t.id
            WHERE a.owner_id=? AND t.date BETWEEN ? AND ? ORDER BY t.date,t.created_at,t.id LIMIT 10001''', (user.id, start.isoformat(), end.isoformat()))]
        if len(rows) > 10000:
            raise HTTPException(400, 'Choose a shorter statement period (maximum 10,000 transactions).')
        totals, boundary = statement_totals(conn, user.id, start, end)
    headings = ['Date', 'Reference', 'Account', 'Description', 'Direction', 'Amount VND', 'Status', 'Balance after VND', 'Fee VND', 'Total debit VND']
    values = [[r['date'], r['id'], r['account_id'], r['description'], r['direction'], r['amount_vnd'], r['status'],
               r['balance_after_vnd'] if r['balance_after_vnd'] is not None else r['product_balance'], r['fee_vnd'],
               r['amount_vnd'] + r['fee_vnd'] if r['direction'] == 'out' else 0] for r in rows]
    if fmt == 'csv':
        out = StringIO(newline=''); writer = csv.writer(out); writer.writerow(headings)
        for row in values:
            # Prevent spreadsheet formula execution in customer-supplied descriptions/names.
            writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in row])
        writer.writerow([])
        writer.writerow(['Ledger period summary', 'Account', 'Opening balance VND', 'Total credit VND', 'Total debit VND', 'Closing balance VND'])
        for row in totals:
            writer.writerow(['Account summary', *[v if v is not None else 'Not recorded (pre-ledger)' for v in row]])
        writer.writerow(['Ledger coverage begins', boundary, 'Legacy history is excluded from ledger totals. Pending debits and refunds are included when posted.'])
        return out.getvalue().encode('utf-8-sig')
    out = BytesIO()
    style = ParagraphStyle('statement', fontName='NovaSans', fontSize=8, leading=12)
    p = lambda text: Paragraph(escape(str(text if text is not None else 'Not recorded')), style)
    story = [p('NOVABANK · SIMULATED ACCOUNT STATEMENT'), Spacer(1, 12),
             p(f'{user.name} · {start} to {end}'),
             p('Legacy demo history predates the ledger migration. Balances are shown only where an authoritative snapshot exists.'), Spacer(1, 12)]
    story.append(p(f'Ledger coverage begins {boundary}. Legacy history is excluded from totals. Pending debits and refunds are included when posted.'))
    for account, opening, credit, debit, closing in totals:
        money = lambda value: f'{value:,} VND' if value is not None else 'Not recorded (pre-ledger)'
        story.extend([p(account), p(f'Opening balance: {money(opening)}; Total credit: {money(credit)}'),
                      p(f'Total debit: {money(debit)}; Closing balance: {money(closing)}'), Spacer(1, 12)])
    table_rows = [[p(x) for x in ['Date / reference', 'Description / account', 'Amount / status', 'Balance after']]]
    for row in values:
        table_rows.append([p(row[0] + '\n' + row[1]), p(row[3] + '\n' + row[2]), p(f'{row[4]} {row[5]:,} VND; fee {row[8]:,}\n{row[6]}'), p(f'{row[7]:,}' if row[7] is not None else 'Not recorded')])
    table = LongTable(table_rows, colWidths=[130, 185, 105, 85], repeatRows=1)
    table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'), ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeaf6')),
                              ('BOTTOMPADDING',(0,0),(-1,-1),9), ('LINEBELOW',(0,0),(-1,-1),.3,colors.lightgrey)]))
    story.append(table)
    SimpleDocTemplate(out, pagesize=A4, leftMargin=45, rightMargin=45, title='NovaBank simulated statement').build(story)
    return out.getvalue()
