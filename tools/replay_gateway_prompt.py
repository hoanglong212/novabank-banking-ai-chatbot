"""Replay the archived payload as poisoned ticket data in the isolated research lab.
This is NOT the deployed bank: naive deliberately exposes execute_transfer.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import uuid
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'backend')]
from research.engine import classify,run_case
from research.scenarios import attacks
from research.sandbox import Sandbox


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--repetitions',type=int,choices=range(1,6),default=3)
    args=parser.parse_args()
    directory=ROOT/'.local/research'/('gateway-replay-'+uuid.uuid4().hex[:10])
    directory.mkdir(parents=True)
    args.out.mkdir(parents=True,exist_ok=True)
    scenario=next(c for c in attacks() if c['id']=='support_ticket-01')
    sandbox=Sandbox(directory/'sandbox')
    url=os.environ.get('OLLAMA_URL','http://127.0.0.1:11434')
    rows=[]
    with httpx.Client(timeout=90,trust_env=False) as client:
        verdict=classify(client,url,scenario['payload'])
        for profile in ['naive','baseline','defended']:
            for attempt in range(1,args.repetitions+1):
                # Fixed seed matches the full-matrix successful case; attempts measure reproducibility.
                row=run_case(client,url,sandbox,scenario,'qwen2.5:7b',profile,0,verdict,seed=20261101)
                row['attempt']=attempt
                rows.append(row)
                print(json.dumps({'profile':profile,'attempt':attempt,'error':row['error'],
                    'tools':[(c['name'],c['decision'],c.get('result',{})) for c in row['tool_calls']],
                    'balances':row['sandbox']['balances']}),flush=True)
    (args.out/'replay.json').write_text(json.dumps({'scenario':scenario,'classifier':verdict,
        'fixed_seed':20261101,'temperature':0.2,'run_directory':str(directory),'observations':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    return 1 if any(row['error'] for row in rows) else 0


if __name__=='__main__': raise SystemExit(main())
