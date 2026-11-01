import { useEffect, useState } from 'react';
import type { DemoUser } from '../../types';
import { ConfirmAction, Feedback, Loading, send, useOperation, useResource, type ActionDraft } from '../explore/shared';
import { Sheet } from '../ui/Sheet';
import { vnd } from '../../format';

interface Approval { id: string; name: string; status: string; arguments: Record<string, string | number>; expires_at: number }
interface Run { id: string; status: string; model: string; profile: string; latency_ms: number | null; input_tokens: number; output_tokens: number }
interface Trace extends Run { tool_calls: { id: string; name: string; decision: string; reason: string; latency_ms: number; arguments: unknown; result: unknown }[] }
export function AgentActivity({ user, conversationId, revision, openTransfer }: { user: DemoUser; conversationId: string; revision: number; openTransfer: (id: string) => void }) {
  const approvals = useResource<{ items: Approval[] }>(user, '/agent/approvals?conversation_id=' + conversationId);
  const runs = useResource<{ items: Run[] }>(user, '/agent/runs?conversation_id=' + conversationId);
  const [draft, setDraft] = useState<ActionDraft | null>(null); const [selected, setSelected] = useState<string | null>(null); const op = useOperation();
  useEffect(() => { approvals.reload(); runs.reload(); }, [revision, approvals.reload, runs.reload]);
  async function decide(id: string, approve: boolean) {
    await op.run(async () => { const result = await send<{ message: string; draft_id?: string; action?: ActionDraft }>(user, '/agent/approvals/' + id, { approve }); approvals.reload(); op.setMessage(result.message); if (result.draft_id) openTransfer(result.draft_id); if (result.action) setDraft(result.action); });
  }
  const labels: Record<string, string> = { prepare_transfer: 'Transfer proposal', prepare_bill_payment: 'Bill payment proposal', prepare_support_ticket: 'Support ticket proposal', request_card_freeze: 'Card freeze proposal' };
  return <div className="service-stack agent-review"><Feedback state={op} />{approvals.error && <Loading state={approvals} />}{approvals.data?.items.filter(a => a.status === 'PENDING').map(a => <section className="card service-section" key={a.id}><h3>{labels[a.name] ?? 'Action proposal'}</h3><p className="muted small">Review the details. Approving a payment opens a separate OTP confirmation; it does not move money.</p><dl className="detail-list">{Object.entries(a.arguments).map(([k, v]) => <div key={k}><dt>{k.replaceAll('_', ' ')}</dt><dd>{k === 'amount_vnd' ? vnd(Number(v)) : String(v)}</dd></div>)}</dl><div className="inline-actions"><button className="primary-button" disabled={op.busy || a.expires_at * 1000 < Date.now()} onClick={() => void decide(a.id, true)}>Review and approve</button><button className="secondary-button" disabled={op.busy} onClick={() => void decide(a.id, false)}>Decline</button></div></section>)}
    {!!runs.data?.items.length && <details><summary>Assistant runs and sources ({runs.data.items.length})</summary><ul className="service-list">{runs.data.items.map(r => <li key={r.id}><div><strong>{r.model} · {r.profile}</strong><small>{r.status} · {r.latency_ms == null ? 'Running' : `${(r.latency_ms / 1000).toFixed(1)} s`} · {r.input_tokens + r.output_tokens} tokens</small></div><button className="link-button" onClick={() => setSelected(r.id)}>View trace</button></li>)}</ul></details>}
    <ConfirmAction user={user} draft={draft} close={() => setDraft(null)} done={result => { setDraft(null); op.setMessage(result.message); approvals.reload(); }} />
    <Sheet open={!!selected} onClose={() => setSelected(null)} title="Assistant run trace" side="right">{selected && <RunTrace key={selected} user={user} id={selected} />}</Sheet>
  </div>;
}
function RunTrace({ user, id }: { user: DemoUser; id: string }) {
  const state = useResource<Trace>(user, '/agent/runs/' + id);
  return <><Loading state={state} />{state.data && <><p>{state.data.model} · {state.data.profile} · {state.data.status}</p><ol className="audit-list">{state.data.tool_calls.map(c => <li key={c.id}><strong>{c.name}</strong><span>{c.decision} · {c.reason} · {c.latency_ms} ms</span>{c.name === 'search_knowledge' && <SourceCards user={user} result={c.result} />}<details><summary>Arguments and result / sources</summary><pre className="trace-json">{JSON.stringify({ arguments: c.arguments, result: c.result }, null, 2)}</pre></details></li>)}</ol></>}</>;
}

function SourceCards({ user, result }: { user: DemoUser; result: unknown }) {
  const sources = result && typeof result === 'object' && 'sources' in result && Array.isArray(result.sources) ? result.sources : [];
  return <>{sources.filter(s => s && typeof s.document_id === 'string' && /^KB-[a-zA-Z0-9-]+$/.test(s.document_id)).map(s => <details key={s.document_id}><summary>Source: {String(s.title)} · {s.document_id}</summary><SourceDocument user={user} id={s.document_id} /></details>)}</>;
}
function SourceDocument({ user, id }: { user: DemoUser; id: string }) {
  const state = useResource<{ content: string; source: string }>(user, '/knowledge/' + encodeURIComponent(id));
  return <><Loading state={state} />{state.data && <><p className="preserve-lines">{state.data.content}</p><small>{state.data.source}</small></>}</>;
}
