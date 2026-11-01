from tests.acceptance_helpers import *
from app import recipient_security


@pytest.fixture(autouse=True)
def recipient_quota_window(monkeypatch):
    # These tests exhaust a single fixed window. Wall-clock rollover during
    # slower/coverage runs must not split their requests across two buckets.
    stamp = recipient_security.timestamp()
    monkeypatch.setattr(recipient_security, 'timestamp', lambda: stamp)


def resolve(client, who, path, account='ACC-BOB-001'):
    payload = {'to_account': account, 'amount_vnd': 1000} if path == '/api/transfers' else {
        'account_id': account, 'bank': 'NovaBank', **({'nickname': 'Saved'} if path.endswith('beneficiaries') else {})}
    return client.post(path, headers=who, json=payload)


def test_TRF_14_paths_share_user_counter_and_failures_count(client):
    who = login(client)
    for _ in range(30):
        assert resolve(client, who, '/api/transfers').status_code == 201
    for path in ('/api/transfers', '/api/customer/beneficiaries/lookup', '/api/customer/beneficiaries'):
        response = resolve(client, who, path)
        assert response.status_code == 429
        assert int(response.headers['Retry-After']) > 0
        assert 'BOB' not in response.text.upper()
    with TestClient(app, client=('different-ip', 1234)) as other:
        assert resolve(other, who, '/api/transfers').status_code == 429


def test_TRF_14_lookup_save_and_invalid_accounts_share_quota(client):
    who = login(client)
    assert resolve(client, who, '/api/customer/beneficiaries/lookup').status_code == 200
    assert resolve(client, who, '/api/customer/beneficiaries').status_code == 201
    for _ in range(28):
        assert resolve(client, who, '/api/customer/beneficiaries/lookup', 'MISSING').status_code == 404
    assert resolve(client, who, '/api/transfers').status_code == 429


def test_TRF_14_ip_quota_survives_user_rotation_and_forwarded_header(client):
    for user, target in [('alice', 'ACC-BOB-001'), ('bob', 'ACC-ALICE-001')]:
        who = login(client, user)
        for _ in range(30):
            assert resolve(client, who, '/api/transfers', target).status_code == 201
    # A fresh user cannot evade the shared IP counter by spoofing a forwarding header.
    who = login(client, 'charlie')
    who['X-Forwarded-For'] = '198.51.100.77'
    assert resolve(client, who, '/api/transfers', 'ACC-ALICE-001').status_code == 429

def test_TRF_14_recipient_lookup_via_draft_is_rate_limited(client):
    who=login(client)
    codes=[client.post('/api/transfers',headers=who,json={'to_account':'ACC-BOB-001','amount_vnd':1000}).status_code for _ in range(40)]
    assert 429 in codes, f'40 recipient-resolving draft requests returned {sorted(set(codes))}; no rate limit at this route'


