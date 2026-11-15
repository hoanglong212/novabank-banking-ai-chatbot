"""Evaluation-only transparent Ollama recorder. Never a banking API backdoor."""
import json
import os
from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
ALLOWED = frozenset(('api/chat', 'api/embed', 'api/tags', 'api/show', 'api/version', 'api/ps'))
CAPTURE_LIMIT = 262144


@app.api_route('/{path:path}', methods=['GET', 'POST'])
async def forward(path: str, request: Request):
    if path not in ALLOWED:
        return Response(status_code=404)
    body = await request.body()
    if len(body) > 2 * 1024 * 1024:
        return Response(status_code=413)
    data = json.loads(body) if body else {}
    messages = data.get('messages', []) if isinstance(data, dict) else []
    primary = any(m.get('role') == 'system' and str(m.get('content', '')).startswith('You are Nova') for m in messages if isinstance(m, dict))
    client = httpx.AsyncClient(timeout=150, trust_env=False)
    try:
        upstream = await client.send(client.build_request(request.method, os.environ['W8_OLLAMA_UPSTREAM'].rstrip('/') + '/' + path,
            content=body, headers={'Content-Type': 'application/json'}), stream=True)
    except httpx.HTTPError:
        await client.aclose()
        return Response(status_code=502)
    async def stream():
        captured = bytearray()
        overflow = False
        try:
            async for chunk in upstream.aiter_bytes():
                if len(captured) + len(chunk) <= CAPTURE_LIMIT:
                    captured.extend(chunk)
                else:
                    overflow = True
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()
            if path == 'api/chat' and primary:
                entry = {'model': data.get('model'), 'primary': True, 'status': upstream.status_code,
                    'input_text': json.dumps(messages, ensure_ascii=False)[:CAPTURE_LIMIT],
                    'response': captured.decode('utf-8', errors='replace'), 'overflow': overflow}
                with Path(os.environ['W8_PROXY_LOG']).open('a', encoding='utf-8') as output:
                    output.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return StreamingResponse(stream(), status_code=upstream.status_code,
        media_type=upstream.headers.get('content-type', 'application/json'))
