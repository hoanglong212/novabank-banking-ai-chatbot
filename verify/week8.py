"""Collect backend and API evidence for one Git revision in a disposable checkout."""
import argparse
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from xml.etree import ElementTree as ET
from week8_report import render

ROOT = Path(__file__).resolve().parents[1]


def write_step_results(out, rev, outcomes, setup_error=None):
    report = {'source_commit': rev, 'steps': outcomes, 'finished': all(code is not None for code in outcomes.values())}
    if setup_error:
        report['setup_error'] = setup_error
    (out/'run.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    suite = ET.Element('testsuite', name='Week 8 verification commands',
                       tests=str(len(outcomes) + int(bool(setup_error))),
                       failures=str(sum(code not in (None, 0) for code in outcomes.values())),
                       errors=str(int(bool(setup_error))), skipped=str(list(outcomes.values()).count(None)))
    props = ET.SubElement(suite, 'properties')
    ET.SubElement(props, 'property', name='source_commit', value=rev)
    if setup_error:
        case = ET.SubElement(suite, 'testcase', classname='Week8.command', name='setup')
        ET.SubElement(case, 'error', message=setup_error)
    for name, code in outcomes.items():
        case = ET.SubElement(suite, 'testcase', classname='Week8.command', name=name)
        if code is None:
            ET.SubElement(case, 'skipped', message='Not run')
        elif code != 0:
            ET.SubElement(case, 'failure', message=f'{name} exited {code}')
    ET.indent(suite)
    ET.ElementTree(suite).write(out/'steps.xml', encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true', help='Install test dependencies into a temporary virtual environment.')
    parser.add_argument('--out', type=Path, default=ROOT/'docs/release/week8/runs')
    args = parser.parse_args()
    rev = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    out = args.out.resolve()/rev
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='novabank-suite-',ignore_cleanup_errors=True) as directory:
        tmp = Path(directory)
        project = tmp/'source'
        steps = [
            ('inventory',['verify/mentor-inventory.py',str(project),str(tmp/'inventory')]),
            ('bank',['verify/mentor-bank.py','--clone',str(project),'--out',str(out/'bank.json')]),
            ('documents',['verify/mentor-rag-api.py']),
            ('backend',['-m','pytest','backend/tests','-q','--tb=no','-p','no:cacheprovider','--junitxml',str(tmp/'backend.xml')]),
        ]
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
                   W8_API_EVIDENCE=str(tmp/'matrix.jsonl'), WEEK8_DOC_API_OUT=str(out/'documents.json'))
        outcomes = dict.fromkeys(name for name, argv in steps)
        write_step_results(out, rev, outcomes)
        try:
            subprocess.run(['git','clone','--quiet','--no-checkout','--no-hardlinks',str(ROOT),str(project)],check=True)
            subprocess.run(['git','checkout','--quiet','--detach',rev],cwd=project,check=True)
            python = sys.executable
            if args.setup:
                runtime = tmp/'venv'
                venv.EnvBuilder(with_pip=True).create(runtime)
                python = str(runtime/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
                subprocess.run([python,'-m','pip','install','-r',str(project/'backend/requirements-dev.txt')],check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            write_step_results(out, rev, outcomes, f'{type(exc).__name__} during checkout or environment setup')
            return 1
        for name, argv in steps:
            print('Running',name,flush=True)
            try:
                outcomes[name] = subprocess.run([python,*argv],cwd=project,env=env).returncode
            except OSError as exc:
                print(name, type(exc).__name__, flush=True)
                outcomes[name] = 1
            if name == 'inventory':
                inventory_output = tmp/'inventory'
                for artifact in inventory_output.glob('*'):
                    if artifact.is_file():
                        shutil.copyfile(artifact, out/artifact.name)
                if (inventory_output/'inventory-matrix.csv').is_file():
                    try:
                        render(out/'inventory-matrix.csv', out/'FUNC_API_TEST_REPORT.md')
                    except (KeyError, OSError, ValueError) as exc:
                        print('Inventory report:', type(exc).__name__, flush=True)
                        outcomes[name] = 1
                elif outcomes[name] == 0:
                    print('Missing inventory matrix', flush=True)
                    outcomes[name] = 1
            if name != 'backend':
                write_step_results(out, rev, outcomes)
        try:
            tree = ET.parse(tmp/'backend.xml')
        except (OSError, ET.ParseError) as exc:
            print('Backend JUnit:', type(exc).__name__, flush=True)
            outcomes['backend'] = outcomes['backend'] or 1
        else:
            for case in tree.iter('testcase'):
                for child in list(case):
                    if child.tag in ('failure','error','skipped'):
                        child.clear()
                    elif child.tag not in ('properties',):
                        case.remove(child)
            for suite in tree.iter('testsuite'):
                suite.set('hostname','local')
                props=ET.SubElement(suite,'properties')
                ET.SubElement(props,'property',name='source_commit',value=rev)
            tree.write(out/'backend.xml',encoding='utf-8',xml_declaration=True)
        write_step_results(out, rev, outcomes)
        return int(any(outcomes.values()))


if __name__=='__main__':
    sys.exit(main())
