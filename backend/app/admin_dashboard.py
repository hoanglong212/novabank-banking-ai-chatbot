"""Read-only, bounded operational dashboard. Transfers are counted once, not per account entry."""
from datetime import datetime, time, timedelta, timezone
from .posting import VIETNAM


def utc_now():
    return datetime.now(timezone.utc)


TRANSFER_SOURCE = '''SELECT t.id,t.owner_id,t.from_account,t.to_bank,t.to_account,t.to_name,t.internal,
    t.amount_vnd,t.content,t.transaction_id,COALESCE(t.completed_at,t.created_at) AS recorded_at,
    CASE WHEN t.status='FAILED' THEN 'FAILED' ELSE COALESCE(s.status,t.status) END AS status,
    COALESCE(s.failure_reason,t.failure_reason) AS failure_reason
    FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
    WHERE t.status!='PENDING_OTP' '''


def dashboard(conn, days):
    instant = utc_now()
    today = instant.astimezone(VIETNAM).date()
    first = today - timedelta(days=days - 1)
    start = datetime.combine(first, time.min, VIETNAM).astimezone(timezone.utc)
    previous_start = start - timedelta(days=days)
    stamp = instant.isoformat(timespec='seconds')

    def totals(lower, upper):
        result = dict(conn.execute(f'''WITH transfers_view AS ({TRANSFER_SOURCE})
            SELECT COUNT(*) AS attempts,
                COALESCE(SUM(status='COMPLETED'),0) AS completed,
                COALESCE(SUM(status='FAILED'),0) AS failed,
                COALESCE(SUM(status='PENDING'),0) AS pending,
                COALESCE(SUM(CASE WHEN status='COMPLETED' THEN amount_vnd ELSE 0 END),0) AS volume_vnd,
                COALESCE(SUM(CASE WHEN status='COMPLETED' AND internal=1 THEN amount_vnd ELSE 0 END),0) AS internal_vnd,
                COALESCE(SUM(CASE WHEN status='COMPLETED' AND internal=0 THEN amount_vnd ELSE 0 END),0) AS external_vnd
            FROM transfers_view WHERE datetime(recorded_at)>=datetime(?) AND datetime(recorded_at)<datetime(?)''',
            (lower.isoformat(), upper.isoformat())).fetchone())
        terminal = result['completed'] + result['failed']
        result['success_rate'] = round(result['completed'] / terminal * 100, 1) if terminal else None
        return result

    # Include rows recorded in this second; use exclusive upper bounds for adjacent periods.
    metrics = totals(start, instant + timedelta(seconds=1))
    previous = totals(previous_start, start)
    daily_rows = {row['date']: dict(row) for row in conn.execute(f'''WITH transfers_view AS ({TRANSFER_SOURCE})
        SELECT date(recorded_at,'+7 hours') AS date,
            SUM(CASE WHEN internal=1 THEN amount_vnd ELSE 0 END) AS internal_vnd,
            SUM(CASE WHEN internal=0 THEN amount_vnd ELSE 0 END) AS external_vnd,COUNT(*) AS completed
        FROM transfers_view WHERE status='COMPLETED' AND datetime(recorded_at)>=datetime(?)
            AND datetime(recorded_at)<datetime(?) GROUP BY date(recorded_at,'+7 hours')''',
        (start.isoformat(), (instant + timedelta(seconds=1)).isoformat()))}
    daily = []
    for index in range(days):
        day = (first + timedelta(days=index)).isoformat()
        daily.append(daily_rows.get(day, dict(date=day, internal_vnd=0, external_vnd=0, completed=0)))

    snapshot = dict(conn.execute('''SELECT COUNT(*) AS customers,
        COALESCE(SUM(u.status='ACTIVE'),0) AS active_customers,
        COALESCE(SUM(u.status='ACTIVE' AND COALESCE(p.kyc_status,'UNVERIFIED')='UNVERIFIED'),0) AS unverified_customers
        FROM users u LEFT JOIN customer_profiles p ON p.user_id=u.id WHERE u.role='customer' ''').fetchone())
    snapshot.update(dict(conn.execute('''SELECT COUNT(*) AS accounts,
        COALESCE(SUM(balance_vnd),0) AS payment_balance_vnd,
        COALESCE(SUM(status='FROZEN'),0) AS frozen_accounts FROM accounts''').fetchone()))
    snapshot['open_tickets'] = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status IN ('OPEN','IN_PROGRESS')").fetchone()[0]
    snapshot['pending_settlements'] = conn.execute("SELECT COUNT(*) FROM interbank_settlements WHERE status='PENDING'").fetchone()[0]

    def rows(where, params=(), limit=20, order='recorded_at DESC,id DESC'):
        return [dict(row) for row in conn.execute(f'''WITH transfers_view AS ({TRANSFER_SOURCE})
            SELECT * FROM transfers_view WHERE {where} ORDER BY {order} LIMIT ?''', (*params, limit))]

    bounds = (start.isoformat(), (instant + timedelta(seconds=1)).isoformat())
    in_period = 'datetime(recorded_at)>=datetime(?) AND datetime(recorded_at)<datetime(?)'
    events = [dict(row) for row in conn.execute('''SELECT id,owner_id,action,resource_id,created_at
        FROM banking_audit ORDER BY created_at DESC,rowid DESC LIMIT 5''')]
    return dict(updated_at=stamp,
                period=dict(days=days, from_date=first.isoformat(), to_date=today.isoformat(), timezone='Asia/Ho_Chi_Minh'),
                metrics=metrics, previous=previous, snapshot=snapshot, daily=daily,
                recent=rows(in_period, bounds, limit=8),
                queues=dict(pending=rows("status='PENDING'", order='recorded_at,id'),
                            failed=rows("status='FAILED' AND " + in_period, bounds)), events=events)
