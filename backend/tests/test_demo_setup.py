import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_mock_readiness_does_not_need_ollama(client):
    response = client.get('/api/ready')
    assert response.status_code == 200
    assert response.json()['status'] == 'ready'
    assert response.json()['llm_provider'] == 'mock'


@pytest.mark.parametrize('failure', ['offline', 'missing_model', 'malformed'])
def test_readiness_reports_unusable_ollama(client, monkeypatch, failure):
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    def transport(request):
        if failure == 'offline':
            raise httpx.ConnectError('offline', request=request)
        if failure == 'missing_model':
            return httpx.Response(404, json={'error': 'model not found'})
        return httpx.Response(200, json={})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(transport)))
    response = client.get('/api/ready')
    assert response.status_code == 503
    assert response.json()['status'] == 'not_ready'
    assert 'ollama' in response.json()['detail'].lower()
    assert client.get('/api/health').status_code == 200


def test_readiness_recognizes_installed_model(client, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={'details': {'family': 'llama'}}))))
    assert client.get('/api/ready').status_code == 200


def test_single_port_serves_build_without_exposing_source(tmp_path):
    from app.web import mount_frontend
    dist = tmp_path / 'dist'
    (dist / 'assets').mkdir(parents=True)
    (dist / 'index.html').write_text('<html>NovaBank test build</html>')
    (dist / 'assets' / 'app.js').write_text('console.log("demo")')
    (tmp_path / '.env').write_text('SECRET=not-for-browser')
    app = FastAPI()
    @app.get('/api/health')
    def health():
        return {'status': 'ok'}
    mount_frontend(app, dist)
    with TestClient(app) as client:
        assert 'NovaBank test build' in client.get('/').text
        assert client.get('/assets/app.js').status_code == 200
        assert client.get('/api/health').json() == {'status': 'ok'}
        for path in ['/api/missing', '/.env', '/assets/%2e%2e/%2e%2e/.env']:
            assert client.get(path).status_code == 404


def test_missing_frontend_build_fails_with_actionable_error(tmp_path):
    from app.web import mount_frontend
    with pytest.raises(RuntimeError, match='npm run build'):
        mount_frontend(FastAPI(), tmp_path)
