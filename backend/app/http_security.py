"""Bounded JSON bodies and security headers for the API and compiled UI."""
import json
import logging
import time
import uuid

log = logging.getLogger('novabank.http')
if not log.handlers:
    log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)
log.propagate = False


class HttpSecurity:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        started = time.perf_counter(); request_id = uuid.uuid4().hex; status = 500
        max_bytes = 4 * 1024 * 1024
        if scope['method'] in ('POST', 'PUT', 'PATCH'):
            parts, total = [], 0
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b''); total += len(chunk)
                if total > max_bytes:
                    await send({'type': 'http.response.start', 'status': 413, 'headers': [(b'content-type', b'application/json'), (b'cache-control', b'no-store')]})
                    await send({'type': 'http.response.body', 'body': b'{"detail":"Request body exceeds 4 MB."}'})
                    return
                parts.append(chunk)
                if not message.get('more_body'):
                    break
            body, original = b''.join(parts), receive
            first = True
            async def buffered():
                nonlocal first
                if first:
                    first = False
                    return {'type': 'http.request', 'body': body, 'more_body': False}
                return await original()
            receive = buffered
        async def secured(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']; headers = list(message.get('headers', [])); names = {key.lower() for key, _ in headers}
                values = {
                    b'x-content-type-options': b'nosniff', b'x-frame-options': b'DENY', b'referrer-policy': b'no-referrer',
                    b'permissions-policy': b'camera=(), microphone=(), geolocation=()', b'x-request-id': request_id.encode(),
                    b'content-security-policy': b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'; form-action 'self'",
                }
                if scope.get('path') in ('/docs', '/docs/oauth2-redirect', '/redoc'):
                    # FastAPI's documentation shell uses its versioned CDN assets and inline initializer.
                    # This exception is scoped to documentation, never the banking application.
                    values[b'content-security-policy'] = b"default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
                if scope.get('scheme') == 'https':
                    values[b'strict-transport-security'] = b'max-age=31536000'
                if scope.get('path', '').startswith('/api/'):
                    values[b'cache-control'] = b'no-store'
                headers.extend((k, v) for k, v in values.items() if k not in names)
                message['headers'] = headers
            await send(message)
        try:
            from .recipient_security import peer_address
            # ASGI peer only: arbitrary X-Forwarded-For values are not trusted.
            peer_token = peer_address.set((scope.get('client') or ('unknown',))[0])
            await self.app(scope, receive, secured)
        finally:
            peer_address.reset(peer_token)
            # Paths can include identifiers; never log query strings, request bodies or credentials.
            log.info(json.dumps({'event': 'http_request', 'request_id': request_id, 'method': scope['method'],
                'status': status, 'elapsed_ms': round((time.perf_counter()-started)*1000)}))
