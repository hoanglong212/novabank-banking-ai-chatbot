"""Exercise exit codes and evidence writers with captured, offline observations."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mentor_doc_contracts import offline_checks


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidenceTests(unittest.TestCase):
    def current_oversize(self):
        return {'contract_version': 2, 'http': 422, 'body': {'detail': 'FILE_TOO_LARGE'},
                'documents_before': 7, 'documents_after': 7, 'chunks_before': 3, 'chunks_after': 3}

    def setUp(self):
        data_file = HERE.parent/'docs/release/week8/verify-evidence/rag-api.json'
        self.observed = json.loads(data_file.read_text(encoding='utf-8'))['results']

    def test_document_gate_scores_only_its_offline_evidence(self):
        data = copy.deepcopy(self.observed)
        self.assertEqual(list(offline_checks(data).values()), [True] * 12)
        data['DOC-API-10']['chunks_after'] = 1
        del data['DOC-API-04']['encrypted']
        data['DOC-API-09']['sequential_upload_statuses'] = [201, 500, 429]
        self.assertEqual({k for k, v in offline_checks(data).items() if not v},
                         {'DOC-API-04', 'DOC-API-09', 'DOC-API-10'})
        del data['DOC-API-12']
        self.assertFalse(offline_checks(data)['DOC-API-12'])

    def test_oversized_upload_requires_early_rejection_and_unchanged_db(self):
        data = copy.deepcopy(self.observed)
        historic = data['DOC-API-04']['oversize']
        self.assertTrue(offline_checks(data)['DOC-API-04'])
        self.assertFalse(offline_checks(data, require_current_upload=True)['DOC-API-04'])
        for changes in [{}, {'http': 201}, {'documents_after': 8}, {'chunks_after': 4},
                        {'body': {'detail': 'FILE_TOO_LARGE', 'id': 'unexpected'}}, {'contract_version': 3}]:
            with self.subTest(changes=changes):
                data['DOC-API-04']['oversize'] = {**self.current_oversize(), **changes}
                self.assertEqual(offline_checks(data)['DOC-API-04'], not changes)
                self.assertEqual(offline_checks(data, require_current_upload=True)['DOC-API-04'], not changes)
        data['DOC-API-04']['oversize'] = {**historic, 'contract_version': 2}
        self.assertFalse(offline_checks(data)['DOC-API-04'])

    def test_document_cli_propagates_failure(self):
        module = load_script('mentor-rag-api')
        for value, code in [(0, 0), (1, 1)]:
            sample = copy.deepcopy(self.observed)
            sample['DOC-API-04']['oversize'] = self.current_oversize()
            sample['DOC-API-10']['chunks_after'] = value
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp)/'documents.json'
                with (patch.object(module, 'OUT', dest),
                      patch.dict(module.os.environ),
                      patch.object(module, 'verify', side_effect=lambda src, db, results: results.update(sample)),
                      patch.object(module.subprocess, 'check_output', side_effect=['0'*40, b'']),
                      patch.object(module.subprocess, 'run')):
                    self.assertEqual(module.main(), code)
                evidence = json.loads(dest.read_text(encoding='utf-8'))
                self.assertEqual(evidence['offline_checks']['DOC-API-10'], code == 0)
                self.assertEqual(evidence['additional_live_cases'], ['DOC-API-10', 'DOC-API-11'])

    def test_suite_aggregates_steps_including_document_failure(self):
        runner = load_script('week8')
        original_run = subprocess.run
        rev = subprocess.check_output(['git','rev-parse','HEAD'], cwd=runner.ROOT, text=True).strip()
        for doc_code in (0, 1):
            def run(argv, **options):
                if argv[0] == 'git':
                    return original_run(argv, **options)
                if 'verify/mentor-inventory.py' in argv:
                    inventory = Path(argv[-1])
                    inventory.mkdir()
                    row = dict(service='Bank', method='GET', path='/sample', openapi='True', GEN01='PASS',
                               GEN04='N/A', GEN05='N/A', GEN07='PASS', source_commit=rev)
                    with (inventory/'inventory-matrix.csv').open('w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=row.keys())
                        writer.writeheader()
                        writer.writerow(row)
                if '--junitxml' in argv:
                    target = Path(argv[argv.index('--junitxml')+1])
                    target.write_text('<testsuites><testsuite><testcase name="sample"/></testsuite></testsuites>')
                status = doc_code if 'verify/mentor-rag-api.py' in argv else 0
                return subprocess.CompletedProcess(argv, status)

            with self.subTest(doc_code=doc_code), tempfile.TemporaryDirectory() as tmp:
                with patch.object(sys, 'argv', ['week8.py', '--out', tmp]), patch.object(runner.subprocess, 'run', side_effect=run):
                    self.assertEqual(runner.main(), doc_code)
                out = Path(tmp)/rev
                data = json.loads((out/'run.json').read_text(encoding='utf-8'))
                self.assertTrue(data['finished'])
                self.assertEqual(data['steps']['documents'], doc_code)
                suite = ET.parse(out/'steps.xml').getroot()
                self.assertEqual(suite.get('tests'), '4')
                self.assertEqual(suite.get('failures'), str(doc_code))
                self.assertEqual(suite.get('skipped'), '0')
                self.assertTrue((out/'backend.xml').is_file())
                self.assertIn(rev, (out/'FUNC_API_TEST_REPORT.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
