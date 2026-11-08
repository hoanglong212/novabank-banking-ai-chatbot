import { useEffect, useState } from 'react';
import { Activity, LifeBuoy, ReceiptText, Scale, Send, ShieldCheck, SlidersHorizontal, Snowflake, UserCog } from 'lucide-react';
import type { DemoUser } from '../../types';
import { ConfirmAction, Feedback, Loading, send, useOperation, useResource, type ActionDraft } from '../explore/shared';
import { Sheet } from '../ui/Sheet';
import { vnd } from '../../format';
import { navigate } from '../../router';

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
  const labels: Record<string, string> = { prepare_transfer: 'Transfer proposal', prepare_bill_payment: 'Bill payment proposal', prepare_support_ticket: 'Support ticket proposal', request_card_freeze: 'Card freeze proposal', propose_account_status: 'Account status change', propose_customer_update: 'Customer access change', propose_settings_change: 'Bank settings change', propose_reconciliation: 'Ledger reconciliation', propose_ticket_reply: 'Ticket reply draft', propose_ticket_status: 'Ticket status change' };
  const icons: Record<string, typeof Send> = { prepare_transfer: Send, prepare_bill_payment: ReceiptText, prepare_support_ticket: LifeBuoy, request_card_freeze: Snowflake, propose_account_status: Snowflake, propose_settings_change: SlidersHorizontal, propose_customer_update: UserCog, propose_reconciliation: Scale, propose_ticket_reply: LifeBuoy, propose_ticket_status: LifeBuoy };
  const pending = approvals.data?.items.filter(a => a.status === 'PENDING') ?? [];
  return <div className="service-stack agent-review"><Feedback state={op} />{approvals.error && <Loading state={approvals} />}
    {pending.map(a => {
      const Icon = icons[a.name] ?? ShieldCheck;
      const expired = a.expires_at * 1000 < Date.now();
      const { amount_vnd: amount, ...rest } = a.arguments;
      return <section className="card proposal-card" key={a.id} aria-label={labels[a.name] ?? 'Action proposal'}>
        <header className="proposal-head">
          <span className="proposal-icon" aria-hidden="true"><Icon size={20} /></span>
          <div><h3>{labels[a.name] ?? 'Action proposal'}</h3><small>Prepared by Nova · nothing has happened yet</small></div>
          <span className={`proposal-badge ${expired ? 'is-expired' : ''}`}>{expired ? 'Expired' : 'Needs your approval'}</span>
        </header>
        {amount !== undefined && <p className="proposal-amount">{vnd(Number(amount))}</p>}
        <dl className="proposal-details">{Object.entries(rest).map(([k, v]) => <div key={k} className={k === 'body' ? 'is-body' : undefined}><dt>{k.replaceAll('_', ' ')}</dt><dd>{String(v)}</dd></div>)}</dl>
        <p className="proposal-note"><ShieldCheck size={15} aria-hidden="true" />{a.name.startsWith('propose_') ? a.name === 'propose_ticket_reply' ? 'Approving sends this reply to the customer under your name. Read it first.' : 'Approving applies this change immediately under your name.' : 'Approving a payment opens a separate OTP confirmation. It does not move money by itself.'}</p>
        <div className="inline-actions">
          <button className="primary-button" disabled={op.busy || expired} onClick={() => a.name === 'prepare_transfer' ? navigate('/approvals/' + encodeURIComponent(a.id)) : void decide(a.id, true)}>Review and approve</button>
          <button className="secondary-button" disabled={op.busy} onClick={() => void decide(a.id, false)}>Decline</button>
        </div>
      </section>;
    })}
    {!!runs.data?.items.length && <details className="runs-disclosure"><summary><Activity size={15} aria-hidden="true" />Behind the scenes · assistant runs and sources ({runs.data.items.length})</summary><ul className="runs-list">{runs.data.items.map(r => <li key={r.id}><span className={`run-dot ${r.status === 'COMPLETED' ? 'ok' : r.status === 'RUNNING' ? 'busy' : 'bad'}`} aria-hidden="true" /><div><strong>{r.model} · {r.profile}</strong><small>{r.status.toLowerCase()} · {r.latency_ms == null ? 'running' : `${(r.latency_ms / 1000).toFixed(1)} s`} · {r.input_tokens + r.output_tokens} tokens</small></div><button className="link-button" onClick={() => setSelected(r.id)}>View trace</button></li>)}</ul></details>}
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
