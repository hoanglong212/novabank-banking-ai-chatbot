import asyncio
import httpx
import pytest
from app import vietqr
from app.local_qr import decode


CATALOG = [{'bin': '970436', 'code': 'VCB', 'shortName': 'Vietcombank',
            'name': 'Ngân hàng TMCP Ngoại Thương Việt Nam', 'logo': 'https://cdn.vietqr.io/img/VCB.png'}]


@pytest.fixture(autouse=True)
def reset_directory(monkeypatch):
    monkeypatch.setattr(vietqr, '_banks', [])
    monkeypatch.setattr(vietqr, '_remote_banks', [])
    monkeypatch.setattr(vietqr, '_refresh_after', 0)
    monkeypatch.setattr(vietqr, '_bank_lock', asyncio.Lock())


def serve(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(vietqr.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def test_fetches_only_public_directory_and_coalesces_concurrent_requests(monkeypatch):
    calls = []
    def handler(request):
        calls.append((request.method, str(request.url), request.content))
        return httpx.Response(200, json={'code': '00', 'data': CATALOG})
    serve(monkeypatch, handler)
    async def run():
        lists = await asyncio.gather(vietqr.banks(), vietqr.banks(), vietqr.banks())
        assert all(vietqr.find_bank(items, 'VCB')['bin'] == '970436' for items in lists)
        assert lists[0][:3] == vietqr.DEMO_BANKS
        assert await vietqr.banks() == lists[0]
    asyncio.run(run())
    assert calls == [('GET', 'https://api.vietqr.io/v2/banks', b'')]


@pytest.mark.parametrize('body', [{'code': '99', 'data': CATALOG}, {'code': '00', 'data': []}, [], {'code': '00', 'data': [{'bin': 'bad'}]}])
def test_bad_response_retains_cached_directory_and_backs_off(monkeypatch, body):
    calls = []
    monkeypatch.setattr(vietqr, '_remote_banks', CATALOG)
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=body)
    serve(monkeypatch, handler)
    assert asyncio.run(vietqr.banks()) == [*vietqr.DEMO_BANKS, *CATALOG]
    assert asyncio.run(vietqr.banks()) == [*vietqr.DEMO_BANKS, *CATALOG]
    assert len(calls) == 1


def test_network_failure_keeps_demo_banks_and_personal_qr_never_calls_network(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ConnectError('offline', request=request)
    serve(monkeypatch, handler)
    qr = asyncio.run(vietqr.generate('NovaBank', 'ACC-ALICE-001', account_name='ALICE NGUYEN'))
    assert calls == []
    assert qr['source'] == 'novabank_internal' and qr['demo_only'] is True
    assert decode(qr['payload'])['account_no'] == 'ACC-ALICE-001'
    assert asyncio.run(vietqr.banks()) == vietqr.DEMO_BANKS
    assert len(calls) == 1


def test_directory_is_normalized_and_untrusted_logo_origins_removed(monkeypatch):
    serve(monkeypatch, lambda _: httpx.Response(200, json={'code': '00', 'data': [
        *CATALOG, *CATALOG, {'bin': '970422', 'code': 'MB', 'shortName': 'MBBank', 'name': 'MB', 'logo': 'https://elsewhere.example/img/MB.png'},
        {'bin': 'NOVA', 'code': 'NVB', 'shortName': 'Wrong Nova', 'name': 'Wrong Nova'}, None]}))
    banks = asyncio.run(vietqr.banks())
    assert len(banks) == 5
    assert vietqr.find_bank(banks, 'MB')['logo'] == ''
    assert vietqr.find_bank(banks, 'NOVA')['shortName'] == 'NovaBank'


def test_authenticated_api_exposes_directory_without_changing_demo_qr(client, alice, monkeypatch):
    serve(monkeypatch, lambda _: httpx.Response(200, json={'code': '00', 'data': CATALOG}))
    assert client.get('/api/vietqr/banks').status_code == 401
    response = client.get('/api/vietqr/banks', headers=alice)
    assert response.status_code == 200
    assert any(bank['bin'] == '970436' for bank in response.json())
    qr = client.post('/api/vietqr', headers=alice, json={'bank': 'NovaBank', 'account_no': 'ACC-ALICE-001'}).json()
    assert qr['payload'].startswith('NBQR1:') and qr['image'].startswith('data:image/png;base64,')
