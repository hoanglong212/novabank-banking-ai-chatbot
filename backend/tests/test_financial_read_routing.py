from tests.acceptance_helpers import client, login, pytest  # noqa: F401
from tests.test_AI_12 import run_for


@pytest.mark.parametrize(('question', 'expected'), [
    ('What is my credit card balance?', 'get_cards'),
    ('How much is my available credit?', 'get_cards'),
    ('What is my savings balance?', 'get_savings'),
    ('What is the balance of ACC-ALICE-001?', 'get_account_balance'),
    ('What is my payment account balance before paying my card?', 'get_account_balance'),
])
def test_financial_read_hint_matches_the_requested_product(client, question, expected):
    _, _, token = run_for(client, login(client), question)
    response = client.get('/api/agent/context', headers=token)
    assert response.status_code == 200
    assert response.json()['bound_hint']['tool'] == expected
