from tests.acceptance_helpers import *

def test_STM_01_statement_includes_period_totals(client):
    who=login(client); pay(client,who)
    today=date.today().isoformat()
    response=client.get('/api/statements.csv',headers=who,params={'from_date':today,'to_date':today})
    assert response.status_code==200
    text=response.content.decode('utf-8-sig').lower()
    expected=('opening balance','closing balance','total credit')
    missing=[value for value in expected if value not in text]
    assert not missing, f'Statement omits period summary fields: {missing}'


def test_STM_01_period_summary_uses_ledger_and_includes_fees(client):
    who = login(client); admin = login(client, 'admin')
    assert client.patch('/api/admin/settings', headers=admin, json={'transfer_fee_vnd':500}).status_code == 200
    pay(client, who, 2000)
    today = date.today().isoformat()
    response = client.get('/api/statements.csv', headers=who, params={'from_date':today,'to_date':today})
    rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert ['Account summary', 'ACC-ALICE-001', '12500000', '0', '2500', '12497500'] in rows
    assert not any('ACC-BOB-001' in r for r in rows)
    import base64, re, zlib
    pdf = client.get('/api/statements.pdf', headers=who, params={'from_date':today,'to_date':today})
    # Inspect rendered PDF content streams using the standard library, no new dependency.
    streams = []
    for raw in re.findall(rb'stream\r?\n(.*?)endstream', pdf.content, re.S):
        try:
            streams.append(zlib.decompress(base64.a85decode(raw.strip(), adobe=True)).decode('latin-1'))
        except (ValueError, zlib.error):
            continue
    text = '\n'.join(streams)
    for value in ('Opening balance', 'Closing balance', 'Total credit', 'Total debit', '12,497,500'):
        assert value in text


