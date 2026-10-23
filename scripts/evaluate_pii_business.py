"""Re-score frozen PII evidence by authoritative tool outcome, without tuning rules."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.auth import DEMO_USERS
from app.banking_workflow import bind_request, render_result
from app.database import Database
from app.gateway import PolicyGateway
from app.tools import ToolDispatcher


async def main():
    original = json.loads((ROOT/'docs/day1-evaluation-2026-10-23/pii.json').read_text(encoding='utf-8'))
    rows = [r for r in original['rows'] if r['split']=='evaluation']
    output = ROOT/'docs/day1-followup-2026-10-23/pii-business.json'
    if output.exists():
        raise SystemExit('Evidence already exists; do not overwrite')
    results = []
    with tempfile.TemporaryDirectory(prefix='novabank-pii-business-') as temp:
        db = Database(str(Path(temp)/'eval.sqlite3'))
        db.initialize()
        dispatch = ToolDispatcher(db,PolicyGateway(mode='local'))
        async def run(text):
            bound = bind_request([{'role':'user','content':text}])
            cid = db.create_conversation('alice','PII business comparison')['id']
            if bound.reply is not None:
                return {'reply':bound.reply}
            result = await dispatch.run(DEMO_USERS[0],cid,bound.tool,bound.arguments)
            return {'result':result,'reply':render_result(bound,result)}
        for row in rows:
            if not row['workflow_check_applicable']:
                continue
            before,after = await run(row['text']),await run(row['masked'])
            results.append({'id':row['id'],'text':row['text'],'masked':row['masked'],
                            'before':before,'after':after,'business_broken':before!=after})
        # Existing evaluation has one self-balance and three TX controls; list those
        # explicitly rather than silently expanding the held-out dataset.
    false_positives = [{'id':r['id'],'text':r['text'],'masked':r['masked'],
                       'non_pii_spans_masked':[r['text'][start:end] for _,start,end in r['false_positives']]}
                      for r in rows if r['false_positives']]
    summary = {'method':'Execute frozen before/after inputs through real binder + local authorization + dispatcher as Alice, compare authoritative result and rendered response; not full model integration',
               'applicable_cases':len(results),'business_broken':sum(r['business_broken'] for r in results),
               'binding_changed_but_business_preserved':[r['id'] for r in results if not r['business_broken'] and next(x for x in rows if x['id']==r['id'])['workflow_broken']],
               'non_pii_masked_cases':false_positives,'results':results,
               'limitations':['Uses old evaluation, no recognizer changes or tuning','Does not test approved server-side PII mapping (not implemented)','Other 30 evaluation cases not scored for business correctness','No model invocation; self balance/transaction checks limited to frozen corpus']}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=True,indent=2))


if __name__=='__main__':
    asyncio.run(main())
