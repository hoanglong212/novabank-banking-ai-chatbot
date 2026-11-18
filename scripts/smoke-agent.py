"""Verify an already running, disposable NovaBank demo with a real model."""
import argparse
import json
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    parser.add_argument('--balance', action='store_true', help='Require an allowed balance-tool call')
    args = parser.parse_args()
    origin = args.url.rstrip('/')

    def request(path, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        body = json.dumps(data).encode() if data is not None else None
        return urlopen(Request(origin + path, data=body, headers=headers), timeout=150)

    def read(path, data=None, token=None):
        with request(path, data, token) as response:
            return json.load(response)

    ready = read('/api/ready')
    assert ready['llm_provider'] == 'ollama' and ready['status'] == 'ready', ready
    for asset in ('/', '/ocr/runtime/worker.min.js', '/ocr/lang/eng.traineddata'):
        with request(asset) as response:
            assert response.read(1), f'Missing frontend asset: {asset}'
    challenge = read('/api/auth/login', {'username': 'alice', 'password': 'Alice@2026'})['challenge_id']
    otp = read('/api/dev/outbox/challenge', {'challenge_id': challenge})['code']
    session = read('/api/auth/mfa/verify', {'challenge_id': challenge, 'code': otp})
    token = session['access_token']
    conversation = read('/api/conversations', {'title': 'Container smoke check'}, token)['id']
    prompt = 'What is my account balance?' if args.balance else 'Say hello in one short sentence.'
    events = {}
    with request(f'/api/conversations/{conversation}/stream', {'content': prompt}, token) as stream:
        assert stream.headers['Content-Type'].startswith('text/event-stream')
        name = None
        for raw in stream:
            line = raw.decode().strip()
            if line.startswith('event: '):
                name = line[7:]
            elif line.startswith('data: ') and name:
                events[name] = json.loads(line[6:])
    assert 'error' not in events and 'complete' in events, f'Unexpected stream events: {list(events)}'
    trace = read('/api/agent/runs/' + events['run']['run_id'], token=token)
    assert trace['status'] == 'COMPLETED', trace['termination_reason']
    assert trace['model'] == ready['model'] and trace['output_tokens'] > 0 and trace['answer']
    if args.balance:
        assert any(call['name'] == 'get_account_balance' and call['decision'] == 'ALLOW'
                   for call in trace['tool_calls']), 'No allowed balance-tool call'
    print(f"Agent stream completed with {trace['model']} and {trace['output_tokens']} generated tokens.")


if __name__ == '__main__':
    main()
