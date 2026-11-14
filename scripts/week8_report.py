"""Render observed week8 evidence; never replace missing measurements with zeros."""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.week8_core import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.experiment / 'manifest.json').read_text(encoding='utf-8'))
    observations = args.experiment / 'observations.jsonl'
    rows = [json.loads(line) for line in observations.read_text(encoding='utf-8').splitlines() if line.strip()] if observations.exists() else []
    report = summarize(rows, manifest['attempts'])
    (args.experiment / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    columns = ('case_id', 'channel', 'goal', 'kind', 'config', 'model', 'attempt', 'provider', 'status', 'L1', 'L2', 'L3', 'utility', 'source_exposure', 'error')
    with (args.experiment / 'results.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    def shown(value):
        return 'unavailable' if value is None else f'{value:.3f}'
    lines = ['# Week8 measured results', '', f'Commit: `{manifest["commit"]}`. Recorded observations: {len(rows)}. '
        f'Provider: `{manifest["provider"]}`. Subset: `{manifest["subset"]}`.', '',
        '| Config / model | Real attack attempts | L1 | L2 | L3 | ASR after 1 | ASR after budget | Excluded |',
        '|---|---:|---:|---:|---:|---:|---:|---|']
    for key, group in sorted(report['groups'].items()):
        lines.append(f'| {key} | {group["measured_real_attack_attempts"]} | {shown(group["L1_rate"])} | {shown(group["L2_rate"])} | {shown(group["L3_rate"])} | {shown(group["asr_after_1"])} | {shown(group["asr_after_budget"])} | {json.dumps(group["excluded"])} |')
    c = [group for key, group in report['groups'].items() if key.startswith('C|') and group['measured_real_attack_attempts']]
    answer = 'Not established: no eligible real-model C observations.' if not c else ('Observed in the measured subset: C had L1 > 0 and no observed L3 effect.' if any(group['L1_rate'] > 0 for group in c) and all(group['L3_rate'] == 0 for group in c) else 'The measured observations do not establish the requested C hypothesis.')
    lines += ['', answer, '', 'This is an observation about the recorded finite corpus, not a security guarantee.', '', '## Limitations', '']
    lines += ['- ' + item for item in report['limitations']]
    lines += ['- Detector-unavailable trials (including missing Prompt Guard) are excluded, not reported as blocked attacks.',
        '- Individual attempt artifacts retain raw victim model evidence, app trace, source fixture database and filtered answer.',
        '- The raw recorder is evaluation-only and is not a production bank endpoint.',
        '- Per-channel/per-model detail is in results.csv; use status and source_exposure when interpreting denominators.']
    lines += ['', '## Per-channel observed effects', '', '| Channel | Config / model | Eligible attempts | L1 | L3 |', '|---|---|---:|---:|---:|']
    for channel, groups in report['by_channel'].items():
        for key, group in groups.items():
            lines.append(f'| {channel} | {key} | {group["measured_real_attack_attempts"]} | {shown(group["L1_rate"])} | {shown(group["L3_rate"])} |')
    target = args.output or args.experiment / 'RESULTS.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
