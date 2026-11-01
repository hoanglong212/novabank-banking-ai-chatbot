from tests.acceptance_helpers import *
from tests.test_customer_products import confirm
import base64
import re
import zlib


def pdf_text(pdf):
    parts=[]
    for raw in re.findall(rb'stream\r?\n(.*?)endstream',pdf,re.S):
        try:
            stream=zlib.decompress(base64.a85decode(raw.strip(),adobe=True)).decode('latin-1')
            # ReportLab splits escaped XML entities into separate adjacent Tj operators.
            parts.append(''.join(re.findall(r'\(((?:\\.|[^\\)])*)\)\s*Tj',stream)))
        except (ValueError,zlib.error): pass
    return '\n'.join(parts)


@pytest.mark.parametrize('payload',['<script>alert(1)</script>','<img src=x onerror=alert(1)>'])
def test_SEC_06_stored_markup_remains_literal_in_receipt_and_statement(client,payload):
    who=login(client)
    change=client.post('/api/customer/profile/change',headers=who,json={'field':'name','value':payload,'password':'Alice@2026'})
    assert change.status_code==202
    assert confirm(client,who,change.json()).status_code==200
    draft=client.post('/api/transfers',headers=who,json={'to_account':'ACC-BOB-001','amount_vnd':1000,'content':payload}).json()
    paid=client.post('/api/transfers/'+draft['id']+'/confirm',headers=who,json={'otp':draft['demo_otp']}).json()
    today=date.today().isoformat()
    for path,params in [(f"/api/transactions/{paid['transaction_id']}/receipt.pdf",{}),
                        ('/api/statements.pdf',{'from_date':today,'to_date':today})]:
        response=client.get(path,headers=who,params=params)
        assert response.status_code==200 and response.content.startswith(b'%PDF-')
        text=pdf_text(response.content).replace('\\(','(').replace('\\)',')')
        # PDF text operators must contain literal markup, not an interpreted image/script.
        assert payload in text
        assert b'/JavaScript' not in response.content and b'/JS ' not in response.content and b'/OpenAction' not in response.content
