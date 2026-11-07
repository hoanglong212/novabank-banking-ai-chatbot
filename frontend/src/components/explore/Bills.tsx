import { useState } from 'react';
import { ReceiptText, ArrowUpRight, CheckCircle2 } from 'lucide-react';
import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { ConfirmAction, Feedback, Field, Loading, send } from './shared';
import { EmptyState, Metric, ServiceHeading, ServiceNote, displayDate } from './ServiceUi';
import { Sheet } from '../ui/Sheet';
import { useProducts } from './useProducts';

interface Bill { id: string; provider: string; category: string; amount_vnd: number; due_date: string; status: string; saved: number; customer_code: string; paid_at?: string; transaction_id?: string }
export function Bills({ user }: { user: DemoUser }) {
  const p = useProducts<Bill>(user, 'bills');
  const [filter, setFilter] = useState('All'), [category, setCategory] = useState('all'), [selected, setSelected] = useState<Bill | null>(null);
  const items = p.state.data?.items ?? [], unpaid = items.filter(b => b.status === 'UNPAID');
  const visible = items.filter(b => (filter === 'All' || b.status === filter.toUpperCase()) && (category === 'all' || b.category === category));
  return <div className="service-stack"><ServiceHeading eyebrow="ONE LESS THING TO REMEMBER" title="Keep everyday bills in order">Review your due dates, set reminders and pay from your NovaBank account.</ServiceHeading><Loading state={p.state} /><Feedback state={{ error: selected ? '' : p.op.error, message: p.op.message }} />
    {p.state.data && <div className="service-metrics"><Metric label="Amount due" value={vnd(unpaid.reduce((n, b) => n + b.amount_vnd, 0))} /><Metric label="Unpaid bills" value={unpaid.length} note="Ready to review" /><Metric label="Paid bills" value={items.length - unpaid.length} note="Recorded in your activity" /></div>}
    <div className="service-toolbar"><div className="service-filters" aria-label="Bill status">{['All', 'Unpaid', 'Paid'].map(value => <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{value}</button>)}</div><Field label="Bill category"><select value={category} onChange={e => setCategory(e.target.value)}><option value="all">All categories</option>{[...new Set(items.map(b => b.category))].map(c => <option key={c} value={c}>{c[0].toUpperCase() + c.slice(1)}</option>)}</select></Field></div>
    <div className="service-grid">{visible.map(bill => <article className="card service-section" key={bill.id}><div className="service-toolbar"><span className="bill-mark"><ReceiptText size={23} /></span><span className={`service-status ${bill.status.toLowerCase()}`}>{bill.status.toLowerCase()}</span></div><h2 className="card-title">{bill.provider}</h2><strong className="service-amount">{vnd(bill.amount_vnd)}</strong><div className="bill-meta"><span>{bill.customer_code}</span><span>Due {displayDate(bill.due_date)}</span></div>
      <label className="check-field"><input type="checkbox" checked={!!bill.saved} disabled={p.op.busy} onChange={e => { const checked = e.target.checked; void p.op.run(async () => { await send(user, `/bills/${bill.id}/saved?saved=${checked}`, undefined, 'PATCH'); p.state.reload(); p.op.setMessage(checked ? 'Bill reminder saved.' : 'Bill reminder removed.'); }); }} />Save bill and remind me</label>
      <button className={bill.status === 'UNPAID' ? 'primary-button' : 'secondary-button'} onClick={() => setSelected(bill)}>{bill.status === 'UNPAID' ? <>Review payment<ArrowUpRight size={16} /></> : <>View payment<CheckCircle2 size={16} /></>}</button>
    </article>)}</div>
    {!p.state.busy && !p.state.error && !visible.length && <EmptyState title="No bills in this view">Try another category or status. Paid bills stay in your records.</EmptyState>}
    <ServiceNote>Providers and bills are fictional. Payments update your demo balance and transaction history.</ServiceNote>
    <Sheet open={!!selected} title={selected?.status === 'PAID' ? 'Payment details' : 'Pay a bill'} onClose={() => setSelected(null)}>{selected && <div className="service-dialog"><ServiceHeading title={selected.provider}>{selected.customer_code}</ServiceHeading><div className="service-amount-preview"><span>{selected.status === 'PAID' ? 'Paid amount' : 'Amount to pay'}</span><strong>{vnd(selected.amount_vnd)}</strong><small>Due {displayDate(selected.due_date)}</small></div><Feedback state={p.op} />{selected.status === 'UNPAID' ? <><Loading state={p.accounts} /><form className="service-form" onSubmit={e => { e.preventDefault(); p.prepare({ kind: 'PAY_BILL', resource_id: selected.id, account_id: new FormData(e.currentTarget).get('account_id') }); }}><Field label="Pay from"><select name="account_id" required>{p.accounts.data?.items.filter(a => a.status === 'ACTIVE').map(a => <option key={a.id} value={a.id}>{a.nickname} · {vnd(a.balance_vnd)}</option>)}</select></Field><button className="primary-button" disabled={p.op.busy || p.accounts.busy || !p.accounts.data?.items.some(a => a.status === 'ACTIVE')}>Continue to verification</button></form></> : <dl className="detail-list"><div><dt>Status</dt><dd>Paid</dd></div><div><dt>Payment date</dt><dd>{selected.paid_at ? displayDate(selected.paid_at) : 'Recorded'}</dd></div><div><dt>Transaction</dt><dd>{selected.transaction_id ?? 'See activity'}</dd></div></dl>}</div>}</Sheet>
    <ConfirmAction user={user} draft={p.draft} close={() => p.setDraft(null)} done={result => { setSelected(null); p.complete(result); }} />
  </div>;
}
