import pytest


def test_corpus_restores_unicode_without_rewriting_legacy_and_deduplicates_english():
    from research.promptguard_benchmark import build_corpus
    rows = build_corpus()
    vi = [r for r in rows if r['language'].startswith('vi_')]
    assert len(vi) == 52
    assert all('?' not in r['text'] for r in vi)
    assert all(any(ord(c) > 127 for c in r['text']) for r in vi if r['language'] == 'vi_accented')
    assert all(r['text'].isascii() for r in vi if r['language'] == 'vi_unaccented')
    en = [r for r in rows if r['language'] == 'en']
    assert {r['label'] for r in en} == {0, 1}
    assert len({r['text'] for r in en}) == len(en)


def test_split_is_repeatable_half_and_keeps_language_pairs_together():
    from research.promptguard_benchmark import build_corpus, split_corpus
    rows = build_corpus()
    split = split_corpus(rows)
    assert split == split_corpus(list(reversed(rows)))
    assert abs(sum(v == 'calibration' for v in split.values()) - len(rows) / 2) <= 1
    for group in {r['group'] for r in rows}:
        assert len({split[r['id']] for r in rows if r['group'] == group}) == 1
    for language in {r['language'] for r in rows}:
        for part in ('calibration', 'held_out'):
            assert {r['label'] for r in rows if r['language'] == language and split[r['id']] == part} == {0, 1}


def test_calibration_never_uses_held_out_scores_and_reports_real_metrics():
    from research.promptguard_benchmark import summarize_detector
    rows = [{'id': str(i), 'label': i % 2, 'language': 'en'} for i in range(4)]
    split = {'0': 'calibration', '1': 'calibration', '2': 'held_out', '3': 'held_out'}
    outcomes = [{'id': str(i), 'available': True, 'score': score, 'latency_ms': 10.0}
                for i, score in enumerate([0.1, 0.9, 0.8, 0.2])]
    report = summarize_detector(rows, outcomes, split)
    assert report['threshold'] == 0.5
    assert report['held_out']['fp'] == report['held_out']['fn'] == 1
    assert report['held_out']['f1'] == 0
    assert report['held_out']['false_positive_rate'] == 1
    assert report['held_out']['mean_latency_ms'] == 10
    outcomes[2]['score'], outcomes[3]['score'] = 0, 1
    assert summarize_detector(rows, outcomes, split)['threshold'] == report['threshold']


def test_missing_scores_are_not_true_positives_or_successful_calibration():
    from research.promptguard_benchmark import summarize_detector
    rows = [{'id': str(i), 'label': i % 2, 'language': 'en'} for i in range(4)]
    split = {str(i): 'calibration' if i < 2 else 'held_out' for i in range(4)}
    outcomes = [{'id': str(i), 'available': False, 'injection': True, 'latency_ms': 1} for i in range(4)]
    report = summarize_detector(rows, outcomes, split)
    assert report['threshold'] is None
    assert report['held_out']['observed'] == report['held_out']['tp'] == 0
    assert report['held_out']['f1'] is None
    with pytest.raises(ValueError):
        summarize_detector(rows, outcomes[:-1], split)
