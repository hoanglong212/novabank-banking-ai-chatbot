"""Fix round 1, step 2: a transaction line the run's own history read returned is not a debt-balance claim."""
from tests.acceptance_helpers import *
from tests.test_AI_12 import run_for

PROMPT = 'Cho tôi xem giao dịch gần đây.'


def vnd(amount):
    return format(amount, ',').replace(',', '.')


def history_run(client):
    who = login(client)
    _, _, token = run_for(client, who, PROMPT)
    read = client.post('/api/agent/tools', headers=token, json={'name': 'get_recent_transactions', 'arguments': {}}).json()
    assert read['decision'] == 'ALLOW', read
    return token, read['result']['items']


def preview(client, token, answer):
    return client.post('/api/agent/preview', headers=token, json={'answer': answer}).json()['text']


def line(item, amount=None):
    year, month, day = item['date'].split('-')
    return f'{day}/{month}/{year}: Thanh toán nợ thẻ tín dụng - {vnd(amount or item["amount_vnd"])} VND'


def test_own_transaction_line_mentioning_card_debt_is_shown(client):
    token, items = history_run(client)
    answer = 'Đây là các giao dịch gần đây của bạn:\n\n1. Ngày ' + line(items[0]) + '\n2. Ngày ' + line(items[1]) + '\n\nBạn cần thêm gì không?'
    assert preview(client, token, answer) == answer


def test_history_controls_are_still_blocked(client):
    token, items = history_run(client)
    amounts = {i['amount_vnd'] for i in items}
    with get_db().connect() as conn:
        # The test seed may give alice no credit card; any debt figure then stands in for one.
        debt = conn.execute("SELECT MAX(outstanding_vnd) FROM cards WHERE owner_id='alice' AND kind='CREDIT'").fetchone()[0] or 3210000
        balance = conn.execute("SELECT balance_vnd FROM accounts WHERE owner_id='alice'").fetchone()[0]
    missing = next(a for a in range(987654, 10**8, 1000) if a not in amounts)
    year, month, day = items[0]['date'].split('-')
    controls = {
        'real card debt': f'Dư nợ thẻ tín dụng của bạn là {vnd(debt)} VND.',
        'unrequested balance': f'Số dư tài khoản của bạn là {vnd(balance)} VND.',
        'foreign account': f'1. Ngày {day}/{month}/{year}: Chuyển tới ACC-BOB-001 - {vnd(items[0]["amount_vnd"])} VND',
        'amount not in tool result': '1. Ngày ' + line(items[0], missing),
        'no date or description anchor': f'Bạn đã thanh toán nợ thẻ {vnd(items[0]["amount_vnd"])} VND.',
    }
    for name, answer in controls.items():
        assert preview(client, token, answer) != answer, name
