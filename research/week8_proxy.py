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


def is_primary(data):
    messages = data.get('messages', []) if isinstance(data, dict) else []
    return any(m.get('role') == 'system' and str(m.get('content', '')).startswith('You are Nova') for m in messages if isinstance(m, dict))


def tool_names(data):
    """Sorted names of the tools offered in a chat request; names only, never schemas."""
    tools = data.get('tools', []) if isinstance(data, dict) else []
    return sorted(t['function']['name'] for t in tools
                  if isinstance(t, dict) and isinstance(t.get('function'), dict) and isinstance(t['function'].get('name'), str))


def apply_sampling(path, data, env):
    """Registered R2 sampling for the primary answer model only; guard/quarantine calls are untouched."""
    temperature, seed = env.get('W8_SAMPLING_TEMPERATURE'), env.get('W8_SAMPLING_SEED')
    if temperature is None and seed is None:
        return data
    if temperature is None or seed is None:
        raise ValueError('Sampling override needs both temperature and seed')
    value = float(temperature)
    if not 0 <= value <= 2:
        raise ValueError('Sampling temperature outside [0, 2]')
    if path != 'api/chat' or not is_primary(data):
        return data
    return {**data, 'options': {**data.get('options', {}), 'temperature': value, 'seed': int(seed)}}


@app.api_route('/{path:path}', methods=['GET', 'POST'])
async def forward(path: str, request: Request):
    if path not in ALLOWED:
        return Response(status_code=404)
    body = await request.body()
    if len(body) > 2 * 1024 * 1024:
        return Response(status_code=413)
    data = json.loads(body) if body else {}
    messages = data.get('messages', []) if isinstance(data, dict) else []
    primary = is_primary(data)
    sampled = apply_sampling(path, data, os.environ)
    if sampled is not data:
        body = json.dumps(sampled).encode()
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
                    'options': sampled.get('options') if isinstance(sampled, dict) else None,
                    'tool_names': tool_names(data),
                    'input_text': json.dumps(messages, ensure_ascii=False)[:CAPTURE_LIMIT],
                    'response': captured.decode('utf-8', errors='replace'), 'overflow': overflow}
                with Path(os.environ['W8_PROXY_LOG']).open('a', encoding='utf-8') as output:
                    output.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return StreamingResponse(stream(), status_code=upstream.status_code,
        media_type=upstream.headers.get('content-type', 'application/json'))
