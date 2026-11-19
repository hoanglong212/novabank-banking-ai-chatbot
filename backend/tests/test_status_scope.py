"""Purpose-limited customer status replies through preview and finish."""
import pytest

from app.agent_output import NOT_DONE
from tests.test_documents_api import engines, upload  # noqa: F401
from tests.test_documents_gateway import call, config
from tests.test_tier5_status import finish, preview, read
from tests.test_week7 import grant_for


@pytest.fixture(params=list('ABCD'))
def profile(client, monkeypatch, request):
    monkeypatch.setenv('ENV', 'demo')
    config(client, request.param)
    return request.param


@pytest.mark.parametrize('history', [False, True], ids=['document-only', 'with-history'])
def test_paid_invoice_is_attributed_only_to_its_document(client, alice, engines, profile, history):
    sentence = 'The invoice for 150,000 VND has been paid.'
    document = upload(client, alice, sentence.encode(), 'invoice.txt').json()['id']
    question = 'Has this invoice been paid?'
    _, _, token = grant_for(client, alice, f'Document {document}: {question}')
    if history:
        read(client, token, 'get_recent_transactions', limit=5)
    assert call(client, token, document, question)['decision'] == 'ALLOW'
    expected = 'According to document "invoice.txt":\n' + sentence
    assert preview(client, token, sentence) == expected
    assert finish(client, token, sentence) == expected


def test_pin_turn_cannot_publish_unrequested_history(client, alice, profile):
    _, _, token = grant_for(client, alice, 'How do I change my card PIN?')
    read(client, token, 'get_recent_transactions', limit=5)
    claim = 'Your transfer has been confirmed.'
    expected = claim if profile == 'A' else NOT_DONE  # A disables Tier 5.
    assert preview(client, token, claim) == expected
    assert finish(client, token, claim) == expected


def test_followup_with_multiple_specific_lookups_cannot_publish_a_list(client, alice):
    _, _, token = grant_for(client, alice, 'Does Bob actually receive it?')
    for reference in ('TX-1001', 'TX-1002'):
        read(client, token, 'get_transaction_status', transaction_id=reference)
    assert preview(client, token, 'Your transfer has been confirmed.') == NOT_DONE


def test_document_cannot_claim_the_assistant_sent_a_payment(client, alice, engines):
    document = upload(client, alice, b'The invoice has been paid.', 'invoice.txt').json()['id']
    _, _, token = grant_for(client, alice, f'Summarize document {document}')
    assert call(client, token, document)['decision'] == 'ALLOW'
    assert preview(client, token, 'I have paid the invoice.') == NOT_DONE
