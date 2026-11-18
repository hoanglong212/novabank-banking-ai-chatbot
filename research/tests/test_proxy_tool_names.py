"""Fix round 1, step 4: primary proxy entries record the sorted tool names sent to the model; the request is unchanged."""
import json
import httpx
from fastapi.testclient import TestClient


def test_primary_entry_records_sorted_tool_names_and_forwards_request_unchanged(monkeypatch, tmp_path):
    from research import week8_proxy
    log, sent = tmp_path / 'raw-model.jsonl', []
    monkeypatch.setenv('W8_OLLAMA_UPSTREAM', 'http://upstream')
    monkeypatch.setenv('W8_PROXY_LOG', str(log))
    monkeypatch.delenv('W8_SAMPLING_TEMPERATURE', raising=False)
    monkeypatch.delenv('W8_SAMPLING_SEED', raising=False)

    def upstream(request):
        sent.append(request.content)
        return httpx.Response(200, json={'message': {'role': 'assistant', 'content': 'ok'}, 'done': True})
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real(transport=httpx.MockTransport(upstream)))

    schema = {'type': 'object', 'properties': {'limit': {'type': 'integer'}}}
    body = json.dumps({'model': 'qwen2.5:7b', 'stream': False, 'options': {'temperature': 0},
                       'messages': [{'role': 'system', 'content': 'You are Nova, ...'}, {'role': 'user', 'content': 'hi'}],
                       'tools': [{'type': 'function', 'function': {'name': 'prepare_support_ticket', 'parameters': schema}},
                                 {'type': 'function', 'function': {'name': 'get_accounts', 'parameters': schema}}]}).encode()
    guard = json.dumps({'model': 'qwen2.5:7b', 'messages': [{'role': 'system', 'content': 'Classify'}]}).encode()
    client = TestClient(week8_proxy.app)
    for payload in (body, guard):
        assert client.post('/api/chat', content=payload, headers={'Content-Type': 'application/json'}).status_code == 200

    assert sent == [body, guard]
    entries = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
    assert len(entries) == 1 and entries[0]['primary'] is True
    assert entries[0]['tool_names'] == ['get_accounts', 'prepare_support_ticket']
    assert 'properties' not in json.dumps(entries[0])


def test_primary_entry_without_tools_records_an_empty_list():
    from research.week8_proxy import tool_names
    assert tool_names({'messages': []}) == []
    assert tool_names({'tools': [{'function': {'name': 'b'}}, {'function': {'name': 'a'}}, {'bad': 1}, 'x']}) == ['a', 'b']
