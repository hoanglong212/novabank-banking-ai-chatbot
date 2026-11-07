from tests.acceptance_helpers import *


def test_notifications_split_into_transaction_and_account_tabs(client):
    who = login(client)
    with get_db().connect() as conn:
        for kind, title in (('MONEY_IN', 'Money received'), ('SECURITY', 'Profile updated'), ('BILL', 'Bill due soon')):
            conn.execute('INSERT INTO service_notifications VALUES (?,?,?,?,?,NULL,NULL,?,NULL,NULL)',
                         ('N-' + kind, 'alice', kind, title, 'body', '2026-11-07T01:00:00+00:00'))
    every = client.get('/api/notifications', headers=who).json()
    money = client.get('/api/notifications?category=transactions', headers=who).json()
    account = client.get('/api/notifications?category=account', headers=who).json()
    assert {r['kind'] for r in money['items']} <= {'MONEY_IN', 'MONEY_OUT', 'TRANSFER', 'REFUND', 'BILL'}
    assert {'MONEY_IN', 'BILL'} <= {r['kind'] for r in money['items']}
    assert [r['kind'] for r in account['items']] == ['SECURITY']
    assert money['total'] + account['total'] == every['total']
    assert every['unread_by_category'] == {'transactions': money['unread_count'], 'account': 1}
    # Marking one tab read leaves the other untouched.
    client.post('/api/notifications/read-all?category=account', headers=who)
    after = client.get('/api/notifications', headers=who).json()
    assert after['unread_by_category'] == {'transactions': money['unread_count'], 'account': 0}
    assert client.get('/api/notifications?category=other', headers=who).status_code == 422


def test_bank_announcements_are_separate_from_personal_unread(client):
    who = login(client)
    before = client.get('/api/notifications', headers=who).json()['unread_count']
    news = client.get('/api/announcements', headers=who).json()['items']
    assert news and all(n['kind'] in ('CAMPAIGN', 'NOTICE') for n in news)
    assert all(n['action_path'] is None or n['action_path'].startswith('/') for n in news)
    assert client.get('/api/notifications', headers=who).json()['unread_count'] == before
    assert client.get('/api/announcements').status_code == 401


def test_notification_search_and_unread_filter(client):
    who = login(client)
    with get_db().connect() as conn:
        for nid, title, body, read in (('S-1', 'Card blocked', 'Card ending 4242', None),
                                       ('S-2', 'Money received', '5,000 VND from BOB', '2026-11-07T02:00:00+00:00'),
                                       ('S-3', 'Promo 100%', 'literal percent', None)):
            conn.execute('INSERT INTO service_notifications VALUES (?,?,?,?,?,NULL,NULL,?,?,NULL)',
                         (nid, 'alice', 'CARD' if nid == 'S-1' else 'MONEY_IN', title, body, '2026-11-07T01:00:00+00:00', read))
    find = lambda query: [r['id'] for r in client.get('/api/notifications?' + query, headers=who).json()['items'] if r['id'].startswith('S-')]
    assert find('q=4242') == ['S-1']                         # matches body
    assert find('q=money%20received') == ['S-2']             # case-insensitive title
    assert find('q=100%25') == ['S-3']                       # % is literal, not a wildcard
    assert 'S-2' not in find('unread=true')
    assert find('q=card&category=transactions') == []        # combines with the tab
    assert client.get('/api/notifications?q=' + 'x' * 101, headers=who).status_code == 422
