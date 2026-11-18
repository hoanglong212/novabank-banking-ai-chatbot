"""Replay the existing local A–J harness on two disposable application revisions."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.week8_runtime import servers, source_identity

def execute(project,harness,out,ollama,configs):
    project=project.resolve()
    (out/'source.json').write_text(json.dumps(source_identity(project),indent=2),encoding='utf-8')
    copied=out/'harness'
    copied.mkdir()
    for path in harness.glob('*.py'):
        shutil.copy2(path,copied/path.name)
    original=(copied/'harness.py').read_text(encoding='utf-8')
    outcomes=[]
    for cfg in configs:
        # Positive tests enroll a real TOTP authenticator and settle money.
        # Each configuration needs a fresh disposable DB, not a weakened login.
        directory=out/('servers-'+cfg+'-'+uuid.uuid4().hex[:8])
        with servers(project,project/'.local/week8-evaluation',directory,'ollama','qwen2.5:7b',ollama,sys.executable) as (url,db):
            text=original.replace("BASE = 'http://127.0.0.1:8080'",'BASE = '+repr(url))
            text=text.replace('ROOT = Path(__file__).resolve().parents[2]','ROOT = Path('+repr(str(project))+')')
            text=text.replace("DB = ROOT / '.local/local-deploy/novabank-realistic.sqlite3'",'DB = Path('+repr(str(db))+')')
            text=text.replace("GATEWAY_LOG = ROOT / '.local/local-deploy/novabank-realistic.sqlite3.gateway.jsonl'",'GATEWAY_LOG = Path('+repr(str(db)+'.gateway.jsonl')+')')
            (copied/'harness.py').write_text(text,encoding='utf-8')
            commands=[('llm_attacks.py',['A','B','C','D']),('e_injection.py',[]),('week7.py',[])]
            if cfg=='D':
                commands += [(name,[]) for name in ('deterministic.py','fix_gh2.py','g8.py','extras.py','positives.py','positives2.py')]
            for name,extra in commands:
                if not (copied/name).is_file():
                    outcomes.append({'config':cfg,'script':name,'status':'BLOCKED'})
                    continue
                with (out/(cfg+'-'+name+'.log')).open('w',encoding='utf-8') as log:
                    result=subprocess.run([sys.executable,str(copied/name),*extra],cwd=project,
                        env={**os.environ,'W8_CONFIG':cfg,'PYTHONIOENCODING':'utf-8'},stdout=log,stderr=subprocess.STDOUT)
                outcomes.append({'config':cfg,'script':name,'exit_code':result.returncode})
                (out/'execution.json').write_text(json.dumps(outcomes,indent=2),encoding='utf-8')
                print(project.name,cfg,name,result.returncode,flush=True)
            with httpx.Client(timeout=5) as client:
                client.get(url+'/api/health').raise_for_status()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--harness-dir',type=Path,required=True)
    parser.add_argument('--ollama-url',default='http://127.0.0.1:11436')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--configs',nargs='+',choices=['A','D'],default=['D','A'])
    args=parser.parse_args()
    out=args.out.resolve() if args.out else args.project.resolve()/'.local/week8-evaluation'/('document-baseline-'+uuid.uuid4().hex[:8])
    out.mkdir(parents=True)
    print(out,flush=True)
    execute(args.project,args.harness_dir.resolve(),out,args.ollama_url,args.configs)
