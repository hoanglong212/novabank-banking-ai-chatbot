"""Collect backend and API evidence for one Git revision in a disposable checkout."""
import argparse
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import venv
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


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
        subprocess.run(['git','clone','--quiet','--no-checkout','--local',str(ROOT),str(project)],check=True)
        subprocess.run(['git','checkout','--quiet','--detach',rev],cwd=project,check=True)
        python = sys.executable
        if args.setup:
            runtime = tmp/'venv'
            venv.EnvBuilder(with_pip=True).create(runtime)
            python = str(runtime/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
            subprocess.run([python,'-m','pip','install','-r',str(project/'backend/requirements-dev.txt')],check=True)
        steps = [
            ('inventory',['verify/mentor-inventory.py',str(project),str(out)]),
            ('bank',['verify/mentor-bank.py','--clone',str(project),'--out',str(out/'bank.json')]),
            ('documents',['verify/mentor-rag-api.py']),
            ('backend',['-m','pytest','backend/tests','-q','--tb=no','-p','no:cacheprovider','--junitxml',str(tmp/'backend.xml')]),
        ]
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
                   W8_API_EVIDENCE=str(tmp/'matrix.jsonl'), WEEK8_DOC_API_OUT=str(out/'documents.json'))
        outcomes = {}
        for name, argv in steps:
            print('Running',name,flush=True)
            result = subprocess.run([python,*argv],cwd=project,env=env)
            outcomes[name] = result.returncode
        if (tmp/'backend.xml').exists():
            tree = ET.parse(tmp/'backend.xml')
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
        (out/'run.json').write_text(json.dumps({'source_commit':rev,'steps':outcomes},indent=2)+'\n',encoding='utf-8')
        return int(any(outcomes.values()))


if __name__=='__main__':
    sys.exit(main())
