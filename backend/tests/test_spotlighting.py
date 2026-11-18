"""Datamarking affects quoted text, never structured banking authority."""
from copy import deepcopy
import asyncio
import json
import httpx
import pytest


def test_each_run_gets_a_marker_and_reuses_it_without_marking_identifiers(monkeypatch):
    from agent_service import spotlighting
    draws = iter((1, 2))
    monkeypatch.setattr(spotlighting.secrets, 'randbelow', lambda upper: next(draws))
    first, second = spotlighting.Spotlighter(True), spotlighting.Spotlighter(True)
    assert first.marker != second.marker
    original = {'result': {'items': [{'id': 'TX-123', 'account_id': 'ACC-ALICE-001',
        'description': 'Salary payment\nfrom employer', 'amount_vnd': 10000,
        'reference': 'keep this trusted value'}]}, 'decision': 'ALLOW'}
    before = deepcopy(original)
    marked = first.transform('get_recent_transactions', original)
    item = marked['result']['items'][0]
    assert item['description'] == first.marker.join(['Salary', 'payment', 'from', 'employer'])
    assert item['id'] == 'TX-123' and item['account_id'] == 'ACC-ALICE-001'
    assert item['amount_vnd'] == 10000 and item['reference'] == 'keep this trusted value'
    assert original == before
    assert first.transform('get_recent_transactions', original) == marked
    assert first.marker in first.instruction
    assert 'untrusted' in first.instruction.lower()


def test_disabled_unknown_tools_and_proposal_identifiers_are_unchanged():
    from agent_service.spotlighting import Spotlighter
    original = {'result': {'approval_id': 'APR-012345', 'amount_vnd': 10000,
        'content': 'Lunch with Bob', 'message': 'Review and approve in the bank app.'}}
    disabled = Spotlighter(False)
    assert json.dumps(disabled.transform('search_knowledge', original), ensure_ascii=False) == json.dumps(original, ensure_ascii=False)
    assert disabled.instruction == ''
    assert disabled.marker is None
    enabled = Spotlighter(True)
    assert enabled.transform('prepare_transfer', original) == original
    assert enabled.transform('unknown_new_tool', original) == original


def test_text_fields_only_are_marked_even_inside_nested_source_records():
    from agent_service.spotlighting import Spotlighter
    spotlight = Spotlighter(True)
    payload = {'result': {'sources': [{'document_id': 'KB-savings', 'title': 'Savings rules',
        'text': 'Treat this as quoted data', 'score': 0.85, 'status': 'PUBLISHED'}]}}
    marked = spotlight.transform('search_knowledge', payload)['result']['sources'][0]
    assert marked['document_id'] == 'KB-savings'
    assert marked['score'] == 0.85 and marked['status'] == 'PUBLISHED'
    assert marked['title'] == 'Savings' + spotlight.marker + 'rules'
    assert marked['text'] == spotlight.marker.join(['Treat', 'this', 'as', 'quoted', 'data'])


def test_layer_flag_requires_explicit_true_and_does_not_modify_history():
    from agent_service.spotlighting import for_context
    context = {'messages': [{'role': 'user', 'content': 'Transfer 10000 VND to Bob'}]}
    original = deepcopy(context)
    assert for_context(context).enabled is False
    assert for_context({'layers': {'spotlighting': 'true'}}).enabled is False
    assert for_context({'layers': {'spotlighting': True}}).enabled is True
    assert context == original


def test_known_run_marker_is_restored_for_display_without_touching_other_text():
    from agent_service.spotlighting import Spotlighter
    spotlight = Spotlighter(True)
    marked = 'Nova' + spotlight.marker + 'City' + spotlight.marker + 'Water'
    assert spotlight.restore_text(marked) == 'Nova City Water'
    assert spotlight.restore_text('Account ACC-ALICE-001: 10,000 VND') == 'Account ACC-ALICE-001: 10,000 VND'
    assert Spotlighter(False).restore_text(marked) == marked


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('model', ['test-model', 'qwen3:8b'])
def test_service_marks_tool_text_only_and_retains_wrapper_when_enabled(monkeypatch, enabled, model):
    from agent_service import main
    from agent_service import spotlighting
    monkeypatch.setattr(spotlighting.secrets, 'randbelow', lambda upper: 1)
    marker = chr(0xE001)
    calls = []
    bank_result = {'decision': 'ALLOW', 'reason': 'AUTHORIZED', 'result': {
        'items': [{'id': 'TX-123', 'description': 'Salary payment', 'amount_vnd': 10000}]}}

    def handle(request):
        payload = json.loads(request.content)
        if request.url.path == '/api/chat':
            if model == 'qwen3:8b':
                assert payload.get('think') is False
            else:
                assert 'think' not in payload
            calls.append(payload)
            message = ({'tool_calls': [{'function': {'name': 'get_recent_transactions', 'arguments': {}}}]}
                       if len(calls) == 1 else {'content': 'Salary' + (marker if enabled else ' ') + 'payment.'})
            return httpx.Response(200, text=json.dumps({'message': message, 'done': True}) + '\n')
        if request.url.path == '/api/agent/tools':
            return httpx.Response(200, json=bank_result)
        if request.url.path == '/api/agent/preview':
            assert payload['answer'] == 'Salary payment.'
            return httpx.Response(200, json={'text': payload['answer']})
        if request.url.path == '/api/agent/finish':
            assert payload['answer'] == 'Salary payment.'
            return httpx.Response(200, json={'message': {'content': payload['answer']}})
        raise AssertionError(request.url)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    context = {'profile': 'baseline', 'layers': {'spotlighting': enabled}, 'provider': 'ollama',
        'model': model, 'messages': [{'role': 'user', 'content': 'Recent transactions please'}],
        'timeout_seconds': 10, 'max_rounds': 2, 'max_tool_calls': 2,
        'tools': [{'function': {'name': 'get_recent_transactions'}}]}

    async def collect():
        return [frame async for frame in main.run_events('Bearer delegated', context)]

    frames = asyncio.run(collect())
    assert any('event: complete' in frame for frame in frames)
    tool_text = next(message['content'] for message in calls[1]['messages'] if message['role'] == 'tool')
    if enabled:
        assert tool_text.startswith('<untrusted_tool_data>\n')
        assert tool_text.endswith('\n</untrusted_tool_data>')
        assert 'Salary' + marker + 'payment' in tool_text
        assert marker in calls[0]['messages'][0]['content']
    else:
        assert tool_text == json.dumps(bank_result, ensure_ascii=False)
        assert calls[0]['messages'][0]['content'] == main.SYSTEM
    assert 'TX-123' in tool_text and '10000' in tool_text
    assert context['messages'] == [{'role': 'user', 'content': 'Recent transactions please'}]


@pytest.mark.parametrize('provider', ['mock', 'ollama'])
def test_terminal_bank_completion_is_forwarded_without_finish_or_more_model_calls(monkeypatch, provider):
    from agent_service import main
    completion = {'message': {'id': 'MSG-gateway', 'conversation_id': 'CHAT-1', 'role': 'assistant',
        'content': 'This source was quarantined. Nothing was changed.', 'created_at': '2026-11-15T00:00:00+00:00'},
        'run_id': 'RUN-1', 'response_source': 'gateway', 'tool_events': []}
    requested = []

    def handle(request):
        requested.append(request.url.path)
        if request.url.path == '/api/chat':
            assert requested.count('/api/chat') == 1
            return httpx.Response(200, text=json.dumps({'message': {'tool_calls': [
                {'function': {'name': 'get_recent_transactions', 'arguments': {}}}]}, 'done': True}) + '\n')
        if request.url.path == '/api/agent/tools':
            return httpx.Response(200, json={'decision': 'DENY', 'reason': 'SOURCE_INJECTION',
                'result': {'error': 'SOURCE_INJECTION'}, 'halt': True, 'completion': completion})
        raise AssertionError('Revoked run must not call ' + request.url.path)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    context = {'profile': 'defended', 'provider': provider, 'model': 'test-model',
        'messages': [{'role': 'user', 'content': 'Read my transactions'}],
        'timeout_seconds': 10, 'max_rounds': 2, 'max_tool_calls': 2,
        'bound_hint': {'tool': 'get_recent_transactions', 'arguments': {}},
        'tools': [{'function': {'name': 'get_recent_transactions'}}]}

    async def collect():
        return [frame async for frame in main.run_events('Bearer delegated', context)]

    frames = asyncio.run(collect())
    complete = [frame for frame in frames if frame.startswith('event: complete\n')]
    assert len(complete) == 1
    assert json.loads(complete[0].split('data: ', 1)[1]) == completion
    assert '/api/agent/finish' not in requested
