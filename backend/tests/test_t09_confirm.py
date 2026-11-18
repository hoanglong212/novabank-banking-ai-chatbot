"""T09: the shared prompt tells the model to call the requested tool instead of asking for confirmation in chat."""
import json

import httpx

from tests.agent_acceptance_helpers import calls, exercise
from tests.test_week7 import grant_for

CALL_NOW = ('When the latest user message clearly requests an action and a matching tool is available, call that tool right away; '
            'do not ask for confirmation in chat, because the bank shows its own separate approval screen.')
TICKET = 'Tạo phiếu hỗ trợ: thẻ của tôi bị khóa.'
ARGS = {'subject': 'Card blocked', 'description': 'Thẻ của tôi bị khóa.'}


def tool_results(events):
    return [json.loads(e.split('data: ', 1)[1]) for e in events if e.startswith('event: tool\n') and '"running"' not in e]


def test_call_now_sentence_is_in_the_shared_system_prompt_only():
    from agent_service import main
    assert CALL_NOW in ' '.join(main.SYSTEM.split())
    assert 'confirmation' not in main.HARDENED  # HARDENED is unchanged; the sentence reaches A/B/C/D through SYSTEM


def test_two_turns_ticket_then_yes_records_whether_turn_two_proposes(client, alice, monkeypatch):
    from agent_service import main
    real_client = httpx.AsyncClient
    # Turn 1 (config D): the ticket tool is offered and the prompt sent carries the new sentence.
    cid, _, token = grant_for(client, alice, TICKET)
    payloads, _, _ = exercise(client, monkeypatch, token, [{'content': 'Please confirm if you want to proceed with creating the ticket.'}])
    system = payloads[0]['messages'][0]['content']
    assert system.startswith(main.SYSTEM)
    assert CALL_NOW in ' '.join(system.split())
    assert 'prepare_support_ticket' in {t['function']['name'] for t in payloads[0]['tools']}
    monkeypatch.setattr(main.httpx, 'AsyncClient', real_client)  # exercise() patches it; do not wrap it twice

    # Turn 2: the user answers "có" and a model that waited for it now calls the tool.
    grant = client.post('/api/agent/runs', headers=alice, json={'conversation_id': cid, 'content': 'có', 'profile': 'defended'})
    assert grant.status_code == 201, grant.text
    token2 = {'Authorization': 'Bearer ' + grant.json()['delegated_token']}
    payloads2, _, events2 = exercise(client, monkeypatch, token2, [calls(('prepare_support_ticket', ARGS)), {'content': 'Done.'}])
    offered = {t['function']['name'] for t in payloads2[0]['tools']}
    results = tool_results(events2)
    # Recorded, not fixed here: intent binding reads only "có", so the ticket tool is not in the turn-2 token.
    assert 'prepare_support_ticket' not in offered
    assert results and results[0]['status'] == 'deny' and results[0]['reason'] == 'TOOL_NOT_IN_TOKEN'
