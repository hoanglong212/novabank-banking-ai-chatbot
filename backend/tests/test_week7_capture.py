"""The capture proxy passes traffic through unchanged and keeps secrets out of HAR files."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import httpx
from tests.acceptance_helpers import ROOT  # noqa: F401 - puts the repo root (tools/) on sys.path


def test_proxy_is_transparent_and_redacts_har(tmp_path):
    from tools.capture_http import Recorder, proxy, free_port
    body = json.dumps({'access_token': 'eyJhbGciOi.eyJzdWIi.c2lnbmF0dXJl', 'balance_vnd': 12500000}).encode()

    class Upstream(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

        def log_message(self, *args):
            pass

    upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    recorder = Recorder(tmp_path / 'c.har'); port = free_port()
    server = proxy(port, f'http://127.0.0.1:{upstream.server_port}', 'client-bank', recorder)
    try:
        reply = httpx.post(f'http://127.0.0.1:{port}/api/auth/login', trust_env=False,
                           headers={'Authorization': 'Bearer secret-token'}, json={'username': 'alice', 'password': 'Alice@2026', 'otp': '123456'})
    finally:
        server.shutdown(); server.server_close(); upstream.shutdown(); upstream.server_close()
    assert reply.content == body  # untouched for the client
    har = (tmp_path / 'c.har').read_text(encoding='utf-8')
    for secret in ('Alice@2026', '123456', 'secret-token', 'eyJhbGciOi'):
        assert secret not in har
    entry = json.loads(har)['log']['entries'][0]
    assert entry['comment'] == 'client-bank' and entry['response']['status'] == 200
    assert '12500000' in entry['response']['content']['text'] and '"alice"' in entry['request']['postData']['text']
