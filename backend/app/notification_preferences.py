from .identity import transaction


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=8').fetchone():
        return
    conn.execute('''CREATE TABLE notification_preferences (owner_id TEXT PRIMARY KEY REFERENCES users(id),
        bill_reminders INTEGER NOT NULL DEFAULT 1 CHECK(bill_reminders IN (0,1)),
        budget_alerts INTEGER NOT NULL DEFAULT 1 CHECK(budget_alerts IN (0,1)))''')
    conn.execute('INSERT INTO schema_migrations VALUES (8,?)', (stamp,))


def get(db, owner):
    with db.connect() as conn:
        row = conn.execute('SELECT bill_reminders,budget_alerts FROM notification_preferences WHERE owner_id=?', (owner,)).fetchone()
    return {'bill_reminders': bool(row[0]) if row else True, 'budget_alerts': bool(row[1]) if row else True}


def save(db, owner, bill_reminders, budget_alerts):
    with transaction(db) as conn:
        conn.execute('''INSERT INTO notification_preferences VALUES (?,?,?) ON CONFLICT(owner_id) DO UPDATE SET
            bill_reminders=excluded.bill_reminders,budget_alerts=excluded.budget_alerts''', (owner, int(bill_reminders), int(budget_alerts)))
    return {'message': 'Notification preferences saved.'}


def allows(conn, owner, kind):
    column = {'BILL': 'bill_reminders', 'BUDGET': 'budget_alerts'}.get(kind)
    if not column:
        return True  # Security and money notifications are mandatory.
    row = conn.execute('SELECT ' + column + ' FROM notification_preferences WHERE owner_id=?', (owner,)).fetchone()
    return bool(row[0]) if row else True
