"""Exercise a running demo with temporary conversations; requires backend dependencies."""
import argparse
import re
import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('url', help='Example: http://127.0.0.1:8080')
parser.add_argument('provider', choices=['mock', 'ollama'])
args = parser.parse_args()
base = args.url
expected_provider = args.provider
with httpx.Client(base_url=base, timeout=180) as client:
    home = client.get('/')
    home.raise_for_status()
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', home.text)
    assert assets, 'Expected a compiled frontend with local assets'
    for asset in assets:
        client.get(asset).raise_for_status()
    assert client.get('/api/ready').json()['llm_provider'] == expected_provider
    for path in ('/.env', '/app/main.py', '/api/no-such-endpoint'):
        assert client.get(path).status_code == 404
    alice = {'Authorization': 'Bearer demo-alice-token'}
    bob = {'Authorization': 'Bearer demo-bob-token'}
    created = client.post('/api/conversations', headers=alice, json={'title': 'Setup acceptance test'})
    created.raise_for_status()
    path = '/api/conversations/' + created.json()['id']
    try:
        for prompt, expected in [('What is my account balance?', '12,500,000'),
                                 ('Show balance for ACC-BOB-001', 'blocked')]:
            response = client.post(path + '/messages', headers=alice, json={'content': prompt})
            response.raise_for_status()
            data = response.json()
            assert expected in data['message']['content'].lower(), data
            assert (data['response_source'] == 'mock') == (expected_provider == 'mock')
            print(prompt, data['response_source'], flush=True)
        assert data['tool_events'][-1]['executed'] == 0
        assert data['tool_events'][-1]['reason_code'] == 'ACCOUNT_NOT_OWNED'
        assert client.get(path + '/messages', headers=bob).status_code == 404
        check = client.post(path + '/demo/tool-check', headers=alice, json={
            'tool_name': 'get_account_balance', 'arguments': {}}).json()
        assert check['decision'] == 'ALLOW' and not check['executed']
    finally:
        client.delete(path, headers=alice).raise_for_status()
print('PASS: UI/assets, readiness, own balance, foreign-account denial, user isolation, dry-run, cleanup')
