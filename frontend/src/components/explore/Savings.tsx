import { useState } from 'react';
import { ArrowUpRight, Plus, PiggyBank } from 'lucide-react';
import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { ConfirmAction, Feedback, Field, Loading } from './shared';
import { EmptyState, Metric, ServiceHeading, ServiceNote, displayDate } from './ServiceUi';
import { Sheet } from '../ui/Sheet';
import { useProducts } from './useProducts';

export interface Saving { id: string; label: string; principal_vnd: number; term_months: number; rate_bps: number; projected_interest_vnd: number; maturity_date: string; status: string; interest_paid_vnd: number; events: { id: string; kind: string; amount_vnd: number; created_at: string }[] }
export function Savings({ user }: { user: DemoUser }) {
  const p = useProducts<Saving>(user, 'savings');
  const [opening, setOpening] = useState(false), [filter, setFilter] = useState('Active');
  const [amount, setAmount] = useState('1000000'), [term, setTerm] = useState('6');
  const rates = p.state.data?.rates_bps ?? {};
  const all = p.state.data?.items ?? [], active = all.filter(s => s.status === 'ACTIVE');
  const items = all.filter(s => filter === 'All' || s.status === filter.toUpperCase());
  const projection = Math.floor((Number(amount) || 0) * (rates[term] ?? 0) * Number(term) / 120000);
  return <div className="service-stack"><ServiceHeading eyebrow="BUILD AT YOUR OWN PACE" title="A home for your next chapter" action={<button className="primary-button" disabled={!Object.keys(rates).length} onClick={() => setOpening(true)}><Plus size={17} />Open savings</button>}>Set money aside with a fixed term and a clear return.</ServiceHeading><Loading state={p.state} /><Feedback state={{ error: opening ? '' : p.op.error, message: p.op.message }} />
    {p.state.data && <div className="service-metrics"><Metric label="Total saved" value={vnd(active.reduce((n, s) => n + s.principal_vnd, 0))} /><Metric label="Projected interest" value={vnd(active.reduce((n, s) => n + s.projected_interest_vnd, 0))} note="If held to maturity" /><Metric label="Active deposits" value={active.length} note="Fixed annual rates" /></div>}
    <div className="service-filters" aria-label="Savings status">{['Active', 'Closed', 'All'].map(value => <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{value}</button>)}</div>
    {!p.state.busy && !p.state.error && !items.length && <EmptyState title={filter === 'Active' ? 'Start with something worth saving for' : 'No deposits in this view'}>Open a term deposit from 100,000 VND. Choose a name, an amount and a term.</EmptyState>}
    <div className="service-grid">{items.map(s => <article className="card service-section" key={s.id}><div className="service-toolbar"><PiggyBank size={23} /><span className={`service-status ${s.status.toLowerCase()}`}>{s.status.toLowerCase()}</span></div><h3>{s.label}</h3><strong className="service-amount">{vnd(s.principal_vnd)}</strong><div className="saving-rule" /><dl className="detail-list"><div><dt>Annual rate</dt><dd>{s.rate_bps / 100}%</dd></div><div><dt>Term</dt><dd>{s.term_months} months</dd></div><div><dt>Maturity</dt><dd>{displayDate(s.maturity_date)}</dd></div><div><dt>{s.status === 'ACTIVE' ? 'Projected interest' : 'Interest paid'}</dt><dd>{vnd(s.status === 'ACTIVE' ? s.projected_interest_vnd : s.interest_paid_vnd)}</dd></div></dl>
      {s.status === 'ACTIVE' && <button className="secondary-button" disabled={p.op.busy} onClick={() => p.prepare({ kind: 'WITHDRAW_SAVINGS', resource_id: s.id })}>Review withdrawal<ArrowUpRight size={16} /></button>}
      <details><summary>Deposit history</summary><ul className="service-list">{s.events?.map(event => <li key={event.id}><div><strong>{event.kind === 'OPEN' ? 'Deposit opened' : 'Deposit withdrawn'}</strong><small>{displayDate(event.created_at)}</small></div><span>{vnd(event.amount_vnd)}</span></li>)}</ul></details>
    </article>)}</div>
    <ServiceNote>Interest is paid at maturity. Early withdrawal returns your principal without interest to the original funding account.</ServiceNote>
    <Sheet open={opening} title="Open a savings deposit" onClose={() => setOpening(false)}><div className="service-dialog"><p>Give your savings a purpose. Review everything before confirming.</p><Feedback state={p.op} /><Loading state={p.accounts} /><form className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); p.prepare({ kind: 'OPEN_SAVINGS', account_id: data.get('account_id'), amount_vnd: Number(amount), term_months: Number(term), label: data.get('label') }); }}>
      <Field label="Savings name"><input name="label" maxLength={80} required placeholder="Emergency fund" /></Field><Field label="Fund from"><select name="account_id" required>{p.accounts.data?.items.filter(a => a.status === 'ACTIVE').map(a => <option key={a.id} value={a.id}>{a.nickname} · {vnd(a.balance_vnd)}</option>)}</select></Field>
      <Field label="Deposit (VND)"><input type="number" required min={100000} max={100000000} step={1000} value={amount} onChange={e => setAmount(e.target.value)} /></Field><Field label="Term and annual rate"><select value={term} onChange={e => setTerm(e.target.value)}>{Object.entries(rates).map(([months, rate]) => <option key={months} value={months}>{months} months · {rate / 100}%</option>)}</select></Field>
      <div className="service-amount-preview" aria-live="polite"><span>Estimated interest at maturity</span><strong>{vnd(projection)}</strong><small>Total at maturity: {vnd((Number(amount) || 0) + projection)}. Early withdrawal earns no interest.</small></div><button className="primary-button" disabled={p.op.busy || p.accounts.busy || !p.accounts.data?.items.some(a => a.status === 'ACTIVE')}>Review savings deposit<ArrowUpRight size={16} /></button>
    </form></div></Sheet>
    <ConfirmAction user={user} draft={p.draft} close={() => p.setDraft(null)} done={result => { setOpening(false); setFilter(result.kind === 'WITHDRAW_SAVINGS' ? 'All' : 'Active'); p.complete(result); }} />
  </div>;
}
