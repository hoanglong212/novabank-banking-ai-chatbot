import pytest
from tests.acceptance_helpers import ROOT


def test_regression_subset_uses_exact_ids_and_rejects_missing_cases():
    from tools.live_attack.run import select_cases
    assert {case['id'] for case in select_cases(selected_ids=['legit-savings-01', 'staff-user-count'])} == {
        'legit-savings-01', 'staff-user-count'}
    with pytest.raises(ValueError, match='missing-case'):
        select_cases(selected_ids=['missing-case'])


def test_live_metrics_count_trials_not_tool_rows_and_exclude_errors():
    from tools.live_attack.run import summarize
    rows = [dict(profile='defended', kind='attack', error='', attack_success=False, utility_success=True),
            dict(profile='defended', kind='attack', error='timeout', attack_success=None, utility_success=None),
            dict(profile='defended', kind='legitimate', error='', attack_success=False, utility_success=True)]
    summary = summarize(rows)['defended']
    assert summary['attack_trials'] == 1 and summary['errors'] == 1
    assert summary['targeted_asr'] == 0 and summary['utility_under_attack'] == 1 and summary['benign_utility'] == 1


def test_live_metrics_separate_not_applicable_from_execution_errors():
    from tools.live_attack.run import summarize
    rows = [dict(profile='baseline', kind='attack', error='NOT_APPLICABLE: no canary'),
            dict(profile='baseline', kind='attack', error='timeout')]
    summary = summarize(rows)['baseline']
    assert summary['errors'] == 1
    assert summary['excluded'] == 1
    assert summary['attack_trials'] == 0 and summary['targeted_asr'] is None


def test_lab_fetch_is_absent_in_app_and_blocked_outside_experimental():
    from research.quishing import LabFetch
    from app.agent_access import MODELS
    assert 'fetch_external' not in MODELS
    lab = LabFetch('http://127.0.0.1:9876')
    with pytest.raises(ValueError, match='experimental'):
        lab.fetch('http://127.0.0.1:9876/policy', 'defended')
    for url in ('https://example.com/', 'http://127.0.0.1:9877/', 'http://user@127.0.0.1:9876/', 'http://127.0.0.1:9876/policy?secret=hello'):
        with pytest.raises(ValueError):
            lab.fetch(url, 'experimental')


def test_lab_fetch_rejects_redirect_and_oversized_body():
    import httpx
    from research.quishing import LabFetch
    for response in (httpx.Response(302, headers={'location': 'http://example.com'}), httpx.Response(200, content=b'x' * 40000)):
        transport = httpx.MockTransport(lambda request: response)
        with httpx.Client(transport=transport) as client:
            with pytest.raises(ValueError):
                LabFetch('http://127.0.0.1:9876').fetch('http://127.0.0.1:9876/policy', 'experimental', client=client)


@pytest.mark.parametrize('profile', ['defended', 'experimental'])
def test_model_link_probe_records_native_proposal_and_bank_denial(monkeypatch, profile):
    import json
    import httpx
    from research import quishing
    bank_requests, model_requests = [], []

    def bank_reply(request):
        bank_requests.append((request.url.path, json.loads(request.content)))
        if request.url.path == '/api/conversations':
            return httpx.Response(201, json={'id': 'conversation'})
        if request.url.path == '/api/agent/runs':
            return httpx.Response(201, json={'delegated_token': 'test-only'})
        assert request.url.path == '/api/agent/tools'
        return httpx.Response(200, json={'decision': 'DENY', 'reason': 'USER_INTENT_REQUIRED'})

    def model_reply(request):
        model_requests.append(json.loads(request.content))
        message = {'role': 'assistant', 'content': 'No payment was made.'}
        if len(model_requests) == 1:
            message['tool_calls'] = [{'function': {'name': 'prepare_transfer', 'arguments': {
                'to_account': 'ACC-CHARLIE-001', 'amount_vnd': 1000}}}]
        return httpx.Response(200, json={'message': message})

    bank = httpx.Client(base_url='http://bank', transport=httpx.MockTransport(bank_reply))
    model = httpx.Client(transport=httpx.MockTransport(model_reply))
    monkeypatch.setattr(quishing.httpx, 'Client', lambda **kwargs: model)
    with bank:
        record = quishing.model_probe(bank, {}, 'http://127.0.0.1:9876', profile, 'test-model')
    assert record['payment_proposed'] and record['model_requests'] == 2
    assert record['events'][0]['result']['decision'] == 'DENY'
    assert ('fetch_external' in record['tools']) == (profile == 'experimental')
    assert model_requests[1]['messages'][-1]['role'] == 'tool'
    assert json.loads(model_requests[1]['messages'][-1]['content'])['reason'] == 'USER_INTENT_REQUIRED'
    assert bank_requests[1][1]['profile'] == 'defended'
    assert all('/confirm' not in path for path, _ in bank_requests)
