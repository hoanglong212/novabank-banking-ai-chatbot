"""Explicit known-payee metadata for fixed regression fixtures, never app code.

No TokenClient interception, automatic new-draft verification or runtime flag.
Security cases must not invoke this helper for their new-payee target.
"""
from app.database import now

FIXED_RECIPIENTS = {
    ('NovaBank', 'ACC-ALICE-001'), ('NovaBank', 'ACC-BOB-001'), ('NovaBank', 'ACC-CHARLIE-001'),
    ('Demo Bank A', '1234567890'), ('Demo Bank A', '1234560000'), ('Vietcombank', '0123456789'),
    ('Demo Bank A', '123456789'), ('Demo Bank B', '1234567890'), ('Demo Bank A', '00123456789'),
}


def mark_known(conn, owner_id, to_account, to_bank='NovaBank'):
    if owner_id not in ('alice', 'bob', 'charlie') or (to_bank, to_account) not in FIXED_RECIPIENTS:
        raise ValueError('Only explicitly listed synthetic regression payees may be marked known')
    conn.execute("INSERT INTO verified_payees VALUES (?,lower(?),?,?,NULL,'fixture_known') ON CONFLICT(owner_id,to_bank,to_account) DO NOTHING",
        (owner_id, to_bank, to_account, now()))


def fixed_known_payees(conn):
    """Baseline fixtures model existing payees; new-payee tests explicitly clear them."""
    for owner in ('alice', 'bob', 'charlie'):
        for bank, account in sorted(FIXED_RECIPIENTS):
            if account != 'ACC-' + owner.upper() + '-001':
                mark_known(conn, owner, account, bank)


def verify_new_payee(client, who, transfer_id):
    """Explicit real enrollment + proof for a fresh Alice security test."""
    from app.auth_crypto import totp
    from app.session_security import timestamp
    setup = client.post('/api/auth/mfa/setup', headers=who, json={'password': 'Alice@2026'})
    assert setup.status_code == 200, setup.text
    secret = setup.json()['secret']
    assert client.post('/api/auth/mfa/enable', headers=who, json={'code': totp(secret, timestamp() // 30 - 1)}).status_code == 200
    proof = client.post('/api/transfers/' + transfer_id + '/step-up', headers=who, json={'code': totp(secret, timestamp() // 30)})
    assert proof.status_code == 200, proof.text
    assert proof.json()['verified'] is True
    client.post('/api/auth/pin', headers=who, json={'password': 'Alice@2026', 'pin': '482916'}).raise_for_status()
