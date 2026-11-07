"""Stolen-identity damage limits: burst velocity and first payment to a new recipient."""
from app import transfers
from tests.conftest import transfer_code


def draft(client, headers, amount=100_000):
    return client.post('/api/transfers', headers=headers, json={'to_account': 'ACC-BOB-001', 'amount_vnd': amount})


def confirm(client, headers, t):
    return client.post(f'/api/transfers/{t["id"]}/confirm', headers=headers, json={'otp': transfer_code(t)})


def test_first_transfer_to_new_recipient_is_capped_until_one_completes(client, alice):
    assert draft(client, alice, 11_000_000).json()['detail'] == 'NEW_RECIPIENT_LIMIT_EXCEEDED'
    assert confirm(client, alice, draft(client, alice).json()).status_code == 200
    assert draft(client, alice, 11_000_000).status_code == 201


def test_velocity_limit_is_rechecked_at_confirm_and_expires(client, alice, monkeypatch):
    monkeypatch.setattr(transfers, 'now', lambda: '2026-11-06T10:00:00+00:00')
    drafts = [draft(client, alice).json() for _ in range(transfers.VELOCITY_MAX_TRANSFERS + 1)]
    for t in drafts[:-1]:
        assert confirm(client, alice, t).status_code == 200
    # Drafts made before the burst still cannot exceed it at confirmation.
    assert confirm(client, alice, drafts[-1]).json()['detail'] == 'VELOCITY_LIMIT_EXCEEDED'
    assert draft(client, alice).json()['detail'] == 'VELOCITY_LIMIT_EXCEEDED'
    monkeypatch.setattr(transfers, 'now', lambda: '2026-11-06T10:10:01+00:00')
    assert confirm(client, alice, draft(client, alice).json()).status_code == 200
