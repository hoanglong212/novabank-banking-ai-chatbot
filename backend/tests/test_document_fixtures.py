from pathlib import Path
from pypdf import PdfReader


def test_document_fixtures_are_extractable_and_include_invisible_attack():
    root = Path(__file__).resolve().parents[2] / 'fixtures/documents'
    names = ('benign_invoice', 'benign_loan_contract', 'inj_direct', 'inj_hidden_white',
             'inj_vi_khongdau', 'inj_subtle', 'inj_fake_pseudonym', 'inj_link', 'bob_canary',
             'inj_alias_variant', 'inj_link_variant')
    for name in names:
        text = '\n'.join(page.extract_text() for page in PdfReader(root / (name + '.pdf')).pages)
        assert text.strip(), name
    hidden = PdfReader(root / 'inj_hidden_white.pdf').pages[0].extract_text()
    assert 'ACC-CHARLIE-001' in hidden
    assert 'CANARY-BOB-7F3A' in PdfReader(root / 'bob_canary.pdf').pages[0].extract_text()
    assert '<ACCOUNT_1>' in PdfReader(root / 'inj_alias_variant.pdf').pages[0].extract_text()
    assert 'http://novabank-verify.xyz' in PdfReader(root / 'inj_link_variant.pdf').pages[0].extract_text()
