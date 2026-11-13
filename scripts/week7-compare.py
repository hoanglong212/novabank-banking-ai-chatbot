"""Compare a completed regression subset with the same trials in an earlier run."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sqlite3


def load(directory):
    summary = json.loads((directory / 'summary.json').read_text(encoding='utf-8'))
    with (directory / 'results.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    return summary, rows


def key(row):
    return row['scenario_id'], row['profile'], row['rep']


def describe(rows, summary):
    reasons = Counter()
    db = Path(summary['run_directory']) / 'bank.sqlite3'
    with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        for row in rows:
            if not row['error'] or row['error'].startswith('NOT_APPLICABLE'):
                continue
            run = connection.execute('SELECT termination_reason FROM agent_runs WHERE id=?', (row['run_id'],)).fetchone()
            reasons[(run[0] if run and run[0] else row['error'])] += 1
    applicable = [r for r in rows if not r['error'].startswith('NOT_APPLICABLE')]
    return {'trials': len(rows), 'execution_errors': sum(reasons.values()), 'termination_reasons': dict(reasons),
            'tool_successes': sum(r['utility_success'] == 'True' for r in applicable),
            'applicable_trials': len(applicable),
            'model_declared_in_summary': summary.get('model'), 'run_directory': summary['run_directory']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    before_summary, before_rows = load(args.before)
    after_summary, after_rows = load(args.after)
    index = {key(row): row for row in before_rows}
    if len(index) != len(before_rows) or len({key(r) for r in after_rows}) != len(after_rows):
        raise ValueError('Duplicate scenario/profile/repetition keys')
    paired = [index[key(row)] for row in after_rows]
    before, after = describe(paired, before_summary), describe(after_rows, after_summary)
    result = {'scope': 'Matched selected trials only; original full results are unchanged',
              'before': before, 'after': after}
    (args.after / 'comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    text = '# Qwen — đối chiếu sau sửa trace\n\n'
    text += f"So sánh đúng {len(after_rows)} cặp scenario/profile/repetition, không ghép số liệu này vào full run cũ. Đây là subset chọn theo lỗi đã thấy, không phải ước lượng độc lập cho toàn bộ bộ thử.\n\n"
    text += '| Chỉ số | Trước sửa | Sau sửa |\n|---|---:|---:|\n'
    for label, field in [('Số lượt', 'trials'), ('Lỗi thực thi', 'execution_errors'), ('Tool utility thành công', 'tool_successes')]:
        text += f'| {label} | {before[field]} | {after[field]} |\n'
    text += '\n## Phân loại lỗi\n\n| Nguyên nhân | Trước sửa | Sau sửa |\n|---|---:|---:|\n'
    for reason in sorted(before['termination_reasons'].keys() | after['termination_reasons'].keys()):
        text += f"| {reason} | {before['termination_reasons'].get(reason, 0)} | {after['termination_reasons'].get(reason, 0)} |\n"
    text += '\nUtility ở đây yêu cầu đúng tool/argument của corpus, không chấm ý nghĩa câu trả lời. Một câu trả lời hữu ích dùng tool khác có thể không đạt chỉ số này. Các lần chạy dùng temperature 0 và không gọi confirm payment.\n'
    (args.after / 'comparison.md').write_text(text, encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
