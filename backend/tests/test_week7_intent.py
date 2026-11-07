"""Week 7 capture finding: polite transfer requests were never bound, so the agent never got prepare_transfer."""
import pytest
from app.agent.agent_access import permitted_tools
from app.banking_workflow import bind_request


def intent(text):
    bound = bind_request([{'role': 'user', 'content': text}])
    return {'text': text, 'tool': bound.tool, 'arguments': bound.arguments}


@pytest.mark.parametrize('text', [
    'Prepare a transfer of 10000 VND to ACC-BOB-001.',
    'Please help: Prepare a transfer of 10000 VND to ACC-BOB-001.',
    'Yes, prepare the transfer of 10000 VND to ACC-BOB-001 now.',
    'Could you send 10000 VND to ACC-BOB-001?',
    'Transfer 10k to ACC-BOB-001',
])
def test_transfer_requests_bind_the_users_own_recipient_and_amount(text):
    bound = intent(text)
    assert bound['tool'] == 'create_transfer'
    assert bound['arguments'] == {'to_bank': 'NovaBank', 'to_account': 'ACC-BOB-001', 'amount_vnd': 10000}
    assert 'prepare_transfer' in permitted_tools(bound)


@pytest.mark.parametrize('text', [
    'What is the NovaBank transfer fee?',
    'Summarize my most recent transfer.',
    'Do not send 10000 VND to ACC-BOB-001.',
    'What is my balance?',
    'Do I have enough money to transfer 3 million?',
    'Vậy tôi có đủ tiền chuyển 3 triệu không?',
])
def test_questions_and_negations_do_not_offer_prepare_transfer(text):
    bound = intent(text)
    assert bound['tool'] != 'create_transfer' and 'prepare_transfer' not in permitted_tools(bound)
