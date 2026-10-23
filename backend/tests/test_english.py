import pytest
from .conftest import new_chat
from .test_reliability import model_reply


@pytest.mark.parametrize('mode', ['mock', 'ollama'])
def test_english_suggestion_flows(client, alice, monkeypatch, mode):
    if mode == 'ollama':
        model_reply(monkeypatch, {'role': 'assistant', 'content': ''})
    else:
        monkeypatch.setenv('LLM_PROVIDER', 'mock')
    cid = new_chat(client, alice)
    for prompt, expected in [
        ('Hello', 'Hello'),
        ('Check my account balance', '12,500,000'),
        ('Do I have enough money to transfer 3 million?', 'enough'),
        ('Check transaction TX-1002', '950,000'),
        ('What is VietQR?', 'recipient'),
        ('Create a support ticket for my pending transaction', 'read-only'),
    ]:
        response = client.post(f'/api/conversations/{cid}/messages', headers=alice, json={'content': prompt})
        assert response.status_code == 200
        content = response.json()['message']['content']
        assert expected in content
        assert content.isascii(), content
