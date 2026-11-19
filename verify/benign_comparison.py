"""Measure the 100 published benign tasks against two clean revisions and one synthetic seed."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def checkout(revision, path):
    sha = subprocess.check_output(['git', 'rev-parse', '--verify', revision + '^{commit}'],
                                  cwd=ROOT, text=True).strip()
    subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(path)], check=True)
    subprocess.run(['git', 'checkout', '--quiet', '--detach', sha], cwd=path, check=True)
    return sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='5f0a87a')
    parser.add_argument('--candidate', default='HEAD')
    parser.add_argument('--guard-model', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/release/week8/runs')
    args = parser.parse_args()
    if not args.guard_model.is_dir():
        parser.error('Provide the installed local Prompt Guard model directory')
    with tempfile.TemporaryDirectory(prefix='novabank-benign-', ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        revisions = [(folder/name, checkout(ref, folder/name))
                     for name, ref in [('baseline', args.baseline), ('candidate', args.candidate)]]
        seed = folder/'bank.sqlite3'
        subprocess.run([sys.executable, 'scripts/seed_realistic.py', '--output', str(seed)],
                       cwd=revisions[0][0], check=True, stdout=subprocess.DEVNULL)
        summaries = []
        for path, sha in revisions:
            output = args.output.resolve()/sha/'published-utility-D.json'
            status = subprocess.run([sys.executable, str(ROOT/'verify/mentor-assistant.py'), '--published-utility',
                                     '--repo', str(path), '--seed-db', str(seed), '--guard-model',
                                     str(args.guard_model.resolve()), '--output', str(output)]).returncode
            report = json.loads(output.read_text(encoding='utf-8'))
            summaries.append((report['corpus_sha256'], report['observed'], status))
        if summaries[0][0] != summaries[1][0]:
            raise ValueError('Different corpus fingerprints across revisions')
        return int(any(n != 100 or code for _, n, code in summaries))


if __name__ == '__main__':
    raise SystemExit(main())
