"""Render the acceptance report from a measured route inventory."""
import argparse
import csv
from pathlib import Path
import os


def render(matrix, target):
    with matrix.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    operations = [row for row in rows if row['openapi'] == 'True']
    revisions = {row['source_commit'] for row in operations}
    if len(revisions) != 1:
        raise ValueError('Expected a nonempty inventory for one source commit')
    revision = revisions.pop()
    total = len(operations)
    body = ['# Week 8 API and functionality report', '',
            f'Tested source `{revision}`. The inventory contains {total} OpenAPI operations and '
            f'{len(rows) - total} framework methods or mounts.', '',
            '| Service | Operations exercised | Successful response validated | Forbidden-role checks | Invalid input with unchanged DB |',
            '|---|---:|---:|---:|---:|']
    for service in sorted({row['service'] for row in operations}):
        selected = [row for row in operations if row['service'] == service]
        def tally(key):
            applicable = [r for r in selected if not r[key].startswith('N/A')]
            return f"{sum(r[key].startswith('PASS') for r in applicable)}/{len(applicable)}"
        body.append(f"| {service} | {sum(r['GEN07'].startswith('PASS') for r in selected)}/{len(selected)} | "
                    f"{tally('GEN01')} | {tally('GEN04')} | {tally('GEN05')} |")
    url = os.path.relpath(matrix, target.parent).replace(os.sep, '/')
    body += ['', f'The first coverage column counts the unsupported-method probe. The other columns count '
             f'passing operations over applicable operations. [Recorded matrix]({url})', '',
             '## Rubric decisions', '',
             '- API-04 accepts 400 or 422. Domain checks and request validation can reject the same invalid amount. The balance must stay unchanged.',
             '- TD5 compares the seeded business data and excludes salted password_hash. Hashing identical passwords produces fresh salts.',
             '- FN-TX-08 is N/A while the customer API lacks a cancel-draft route. Cancelling an Agent run has a different effect.',
             '', '## Operation results', '',
             '| Service and endpoint | Input | Expected | Actual | Verdict |', '|---|---|---|---|---|']
    def cell(value):
        return str(value).replace('|', '&#124;').replace('\n', ' ')
    for row in operations:
        inputs = ['valid request from fixture']
        expected = ['declared 2xx schema and media']
        for field, label, status in [('GEN04', 'forbidden roles', '403'), ('GEN05', 'invalid request variants', '422 and identical DB')]:
            if not row[field].startswith('N/A'):
                inputs.append(label)
                expected.append(status)
        actual = [row[field] for field in ('GEN01', 'GEN04', 'GEN05') if not row[field].startswith('N/A')]
        verdict = 'PASS' if all(value.startswith('PASS') for value in actual) else 'OPEN'
        body.append('| ' + ' | '.join(map(cell, [f"{row['service']} {row['method']} `{row['path']}`", ', '.join(inputs),
                                                    ', '.join(expected), '<br>'.join(actual), verdict])) + ' |')
    body += ['', '## Framework methods and mounts', '',
             '| Service | Method and route | Actual response |', '|---|---|---|']
    for row in rows:
        if row['openapi'] != 'True':
            body.append(f"| {row['service']} | {row['method']} `{row['path']}` | {cell(row['GEN01'])} |")
    body += ['', '## Prior verification', '',
             'The independent verification at `0548e99` measured 19/20 correct displayed RAG answers and '
             '16/20 correct structured results. The historical scripts named positives.py and positives2.py '
             'could not be recovered from published branch or pull-request history. The four replacement '
             'functional prompts and the repository’s published 100-case calibration corpus have separate results.']
    target.write_text('\n'.join(body) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    render(args.matrix, args.target)
