"""One command for regression, browser checks, JUnit/HTML and optional real-model matrix."""
import argparse
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-python',help='Existing Python runtime with Prompt Guard dependencies; omission reports live BLOCKED')
    parser.add_argument('--ollama-url',default='http://127.0.0.1:11436')
    parser.add_argument('--baseline-project',type=Path,help='Immutable checkout of the pre-feature revision')
    parser.add_argument('--harness-dir',type=Path,help='Existing local A–J harness directory')
    args=parser.parse_args()
    out=ROOT/'.local/document-rag-evidence'/uuid.uuid4().hex[:10]
    out.mkdir(parents=True)
    jobs=[
        ('Backend and research regression',[sys.executable,'-m','pytest','backend/tests','research/tests','-q','--tb=short',
            '--basetemp',str(out/'tmp'),'--junitxml='+str(out/'tests.xml')],ROOT),
        ('Python lint',[sys.executable,'-m','ruff','check','backend/app','agent_service','research','scripts','tools'],ROOT),
        ('Frontend components',[shutil.which('npm.cmd') or 'npm','run','test:components'],ROOT/'frontend'),
        ('Frontend build',[shutil.which('npm.cmd') or 'npm','run','build'],ROOT/'frontend'),
        ('Browser regression',[shutil.which('npx.cmd') or 'npx','playwright','test'],ROOT/'frontend'),
    ]
    results=[]
    for index,(name,command,cwd) in enumerate(jobs):
        print(name,flush=True)
        with (out/f'{index}.log').open('w',encoding='utf-8') as log:
            try:
                completed=subprocess.run(command,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                status='PASS' if completed.returncode==0 else 'FAIL'
            except OSError:
                status='ERROR'
        results.append({'name':name,'status':status,'log':f'{index}.log'})
    live_status='BLOCKED'
    if args.live_python:
        with (out/'live.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([args.live_python,'scripts/document-rag-live.py','--out',
                str(ROOT/'.local/week8-evaluation'/('document-rag-'+out.name)),'--ollama-url',args.ollama_url],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        live_status='PASS' if result.returncode==0 else 'ERROR'
        data=ROOT/'.local/week8-evaluation'/('document-rag-'+out.name)/'results.json'
        if data.exists():
            statuses={r['status'] for r in json.loads(data.read_text(encoding='utf-8'))['rows']}
            live_status=next((s for s in ('ERROR','FAIL','BLOCKED') if s in statuses),live_status)
    results.append({'name':'Real-model matrix (not inferred from mock tests)','status':live_status,'log':'live.log' if args.live_python else ''})
    baseline_status='BLOCKED'
    if args.live_python and args.baseline_project and args.harness_dir:
        folders=[]
        for label,project in [('before',args.baseline_project.resolve()),('after',ROOT)]:
            evidence=project/'.local/week8-evaluation'/('docrag-'+out.name+'-'+label)
            folders.append(evidence)
            with (out/(label+'.log')).open('w',encoding='utf-8') as log:
                subprocess.run([args.live_python,str(ROOT/'scripts/document-rag-baseline.py'),'--project',str(project),
                    '--harness-dir',str(args.harness_dir.resolve()),'--out',str(evidence),'--ollama-url',args.ollama_url],
                    cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        from research.document_rag_oracles import compare_baselines
        comparison=compare_baselines(*folders)
        (out/'baseline-comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf-8')
        baseline_status=comparison['status']
    results.append({'name':'Old A–J and benign regression comparison','status':baseline_status,'log':'baseline-comparison.json'})
    (out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    rows=''.join('<tr><td>'+html.escape(r['name'])+'</td><td>'+r['status']+'</td><td>'+html.escape(r['log'])+'</td></tr>' for r in results)
    tests=''
    if (out/'tests.xml').exists():
        root=ET.parse(out/'tests.xml')
        tests='<h2>Executed cases</h2><ul>'+''.join('<li>'+html.escape(t.get('classname','')+'.'+t.get('name',''))+
            ': '+('FAIL' if t.find('failure') is not None else 'ERROR' if t.find('error') is not None else 'SKIP' if t.find('skipped') is not None else 'PASS')+'</li>' for t in root.iter('testcase'))+'</ul>'
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Document RAG verification</title><h1>Document RAG verification</h1><table><tr><th>Check</th><th>Status</th><th>Log</th></tr>'+rows+'</table>'+tests,encoding='utf-8')
    print(out/'report.html')
    return 1 if any(r['status'] in ('FAIL','ERROR') for r in results) else 2 if any(r['status']=='BLOCKED' for r in results) else 0

if __name__=='__main__':
    raise SystemExit(main())
