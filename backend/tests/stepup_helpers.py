"""Explicit known-payee metadata for fixed regression fixtures, never app code.

No TokenClient interception, automatic new-draft verification or runtime flag.
Security cases must not invoke this helper for their new-payee target.
"""
from app.database import now

FIXED_RECIPIENTS = {
    ('NovaBank', 'ACC-ALICE-001'), ('NovaBank', 'ACC-BOB-001'), ('NovaBank', 'ACC-CHARLIE-001'),
    ('Demo Bank A', '1234567890'), ('Demo Bank A', '1234560000'), ('Vietcombank', '0123456789'),
}


def mark_known(conn, owner_id, to_account, to_bank='NovaBank'):
    if owner_id not in ('alice', 'bob', 'charlie') or (to_bank, to_account) not in FIXED_RECIPIENTS:
        raise ValueError('Only explicitly listed synthetic regression payees may be marked known')
    conn.execute("INSERT INTO verified_payees VALUES (?,lower(?),?,?,NULL,'fixture_known') ON CONFLICT(owner_id,to_bank,to_account) DO NOTHING",
        (owner_id, to_bank, to_account, now()))


def seed_regression_payees(conn):
    """Call once in disposable test-server fixtures, never production startup."""
    for owner_id in ('alice', 'bob', 'charlie'):
        for bank, account in sorted(FIXED_RECIPIENTS):
            mark_known(conn, owner_id, account, bank)
