"""Real bank/service integration; only the external model HTTP transport is scripted."""
import asyncio
import json
import httpx
from agent_service import main as service
from tests.test_AI_12 import run_for


def exercise(client, monkeypatch, token, responses, context_changes=None, delay=0):
    context = client.get('/api/agent/context', headers=token).json()
    context.update(provider='ollama', **(context_changes or {}))
    payloads, bank_requests = [], []
    original = httpx.AsyncClient

    async def transport(request):
        body = json.loads(request.content) if request.content else None
        if request.url.path == '/api/chat':
            payloads.append(body)
            if body.get('format'):
                return httpx.Response(200, json={'message': {'content': '{"injection":false}'}})
            if delay:
                await asyncio.sleep(delay)
            response = responses[min(sum(p.get('stream') is True for p in payloads)-1, len(responses)-1)]
            return httpx.Response(200, content=json.dumps({
                'message': response, 'done': True, 'prompt_eval_count': 17, 'eval_count': 9})+'\n')
        bank_requests.append((request.url.path, body))
        result = client.request(request.method, request.url.path, headers=token, json=body)
        return httpx.Response(result.status_code, json=result.json())

    monkeypatch.setattr(service.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(transport), **kw))
    async def consume():
        return [event async for event in service.run_events(token['Authorization'], context)]
    events = asyncio.run(consume())
    return payloads, bank_requests, events


def calls(*items):
    return {'tool_calls': [{'function': {'name': name, 'arguments': args}} for name, args in items]}
