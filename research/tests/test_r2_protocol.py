import pytest


def test_r2_renders_fixed_real_targets_and_no_marker_placeholders():
    from research.r2_protocol import DEFAULT_CONTEXT, attack_cases, attack_turns, capability_cases
    cases = attack_cases(DEFAULT_CONTEXT)
    assert len(cases) == len({case['id'] for case in cases}) == 40
    for channel in ('direct_multi', 'qr_memo'):
        for goal in ('M-TRANSFER', 'M-LEAK'):
            cell = [case for case in cases if case['channel'] == channel and case['goal'] == goal]
            assert len(cell) == 10
            assert {case['language'] for case in cell} == {'en', 'vi_accented', 'vi_unaccented'}
    for case in cases:
        turns = attack_turns(case, DEFAULT_CONTEXT)
        assert len(turns) == 3
        assert 'W8_' not in repr((case, turns))
        assert all(case[key] for key in ('source_url', 'adaptation', 'stages'))
        if case['goal'] == 'M-TRANSFER':
            assert 'ACC-CHARLIE-001' in ' '.join(case['stages'])
            assert 'ACC-CHARLIE-001' not in turns[0]
            assert 'ACC-BOB-001' in turns[0]
        if case['channel'] == 'qr_memo':
            assert all(len(stage) <= 80 for stage in case['stages'])
    controls = capability_cases(DEFAULT_CONTEXT)
    assert len(controls) == 10
    assert all('ACC-CHARLIE-001' in c['prompt'] and 'W8_' not in c['prompt'] for c in controls)


def test_r2_context_substitution_never_leaves_the_old_attacker_in_payload():
    from research.r2_protocol import DEFAULT_CONTEXT, attack_cases
    ctx = {**DEFAULT_CONTEXT, 'target_account': 'ACC-DELTA-002'}
    rows = attack_cases(ctx)
    assert all('ACC-CHARLIE-001' not in str(row) for row in rows)
    assert all('ACC-DELTA-002' in ' '.join(r['stages']) for r in rows if r['goal'] == 'M-TRANSFER')


def test_r2_pairing_is_five_seeded_stochastic_runs_and_one_deterministic_run():
    from research.r2_protocol import repetitions
    runs = repetitions()
    assert len(runs) == 6 and sum(r['temperature'] == 0.7 for r in runs) == 5
    assert sum(r['temperature'] == 0 for r in runs) == 1
    assert len({r['seed'] for r in runs}) == 6
    with pytest.raises(ValueError):
        repetitions(model='qwen3:8b')
