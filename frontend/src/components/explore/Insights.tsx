import { useState } from 'react';
import { Plus, Pencil, ArrowUpRight } from 'lucide-react';
import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { Feedback, Field, Loading, send, useOperation, useResource } from './shared';
import { EmptyState, Metric, ServiceHeading, ServiceNote, today, displayDate } from './ServiceUi';
import { Sheet } from '../ui/Sheet';
export { Goals } from './Goals';
export { Statements } from './Statements';

interface Month { month: string; income_vnd: number; expense_vnd: number; net_vnd: number; categories: { category: string; amount_vnd: number }[]; daily: { date: string; amount_vnd: number }[] }
interface Budget { category: string; amount_vnd: number; spent_vnd: number; exceeded: boolean }
interface InsightsData extends Month { previous: Month; budgets: Budget[] }
const title = (value: string) => value[0].toUpperCase() + value.slice(1);
export function Insights({ user }: { user: DemoUser }) {
  const [month, setMonth] = useState(today().slice(0, 7));
  const state = useResource<InsightsData>(user, '/insights?month=' + month);
  const op = useOperation(), d = state.data?.month === month ? state.data : null;
  const [editor, setEditor] = useState<Budget | 'new' | null>(null);
  const editing = editor && editor !== 'new' ? editor : null;
  return <div className="service-stack"><ServiceHeading eyebrow="KNOW WHERE IT GOES" title="A little perspective on your spending" action={<Field label="Month"><input type="month" required value={month} onChange={e => { if (e.target.value) { setMonth(e.target.value); setEditor(null); } }} /></Field>}>Your completed payments, grouped into a clearer monthly picture.</ServiceHeading><Loading state={state} /><Feedback state={{ error: editor ? '' : op.error, message: op.message }} />
    {d && <><div className="service-metrics"><Metric label="Income" value={vnd(d.income_vnd)} note={`Previous month: ${vnd(d.previous.income_vnd)}`} /><Metric label="Spending" value={vnd(d.expense_vnd)} note={`Previous month: ${vnd(d.previous.expense_vnd)}`} /><Metric label="Net flow" value={vnd(d.net_vnd)} note="Income minus spending" /></div>
    <div className="service-split"><section className="card service-section"><h2 className="card-title">Where your money went</h2><div className="spending-chart">{[...d.categories].filter(c => c.amount_vnd > 0).sort((a,b) => b.amount_vnd - a.amount_vnd).map(c => <div key={c.category}><div className="service-toolbar"><span>{title(c.category)}</span><strong>{vnd(c.amount_vnd)}</strong></div><meter min={0} max={Math.max(d.expense_vnd, 1)} value={c.amount_vnd} aria-label={`${c.category}: ${vnd(c.amount_vnd)}`} /><small className="service-hint">{Math.round(c.amount_vnd / d.expense_vnd * 100)}% of spending</small></div>)}</div>{!d.expense_vnd && <EmptyState title="A fresh month">Completed payments will appear here.</EmptyState>}
      {!!d.daily.length && <details><summary>Daily spending breakdown</summary><ul className="service-list">{d.daily.map(day => <li key={day.date}><span>{displayDate(day.date)}</span><strong>{vnd(day.amount_vnd)}</strong></li>)}</ul></details>}
    </section><section className="card service-section"><ServiceHeading title="Monthly budgets" action={<button className="secondary-button" onClick={() => setEditor('new')}><Plus size={16} />Set budget</button>} />{!d.budgets.length && <EmptyState title="Set your own pace">Choose a spending category and a monthly limit.</EmptyState>}{d.budgets.map(b => <div className={`budget-line${b.exceeded ? ' is-exceeded' : ''}`} key={b.category}><div className="service-toolbar"><strong>{title(b.category)}</strong><button className="link-button" aria-label={`Edit ${b.category} budget`} onClick={() => setEditor(b)}><Pencil size={15} />Edit</button></div><progress max={b.amount_vnd} value={Math.min(b.spent_vnd, b.amount_vnd)} aria-label={`${b.category} budget`} /><div className="service-toolbar"><small>{vnd(b.spent_vnd)} of {vnd(b.amount_vnd)}</small><span className="service-status">{b.exceeded ? 'Reached' : 'On track'}</span></div><small className="service-hint">{b.exceeded ? `${vnd(Math.max(0, b.spent_vnd - b.amount_vnd))} over your limit` : `${vnd(b.amount_vnd - b.spent_vnd)} remaining`}</small></div>)}</section></div>
    <ServiceNote>Completed payments and credit purchases count as spending. Savings deposits and credit repayments are excluded to avoid counting the same money twice.</ServiceNote>
    <Sheet open={!!editor} title={editing ? 'Edit monthly budget' : 'Set a monthly budget'} onClose={() => setEditor(null)}><div className="service-dialog"><p>Set a limit for {month}. Saving a category again updates its existing budget.</p><Feedback state={op} /><form key={editing?.category ?? 'new'} className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/insights/budgets', { month, category: data.get('category'), amount_vnd: Number(data.get('amount')) }, 'PUT'); setEditor(null); state.reload(); op.setMessage('Budget saved.'); }); }}><Field label="Category"><select name="category" defaultValue={editing?.category}>{d.categories.map(c => <option key={c.category} value={c.category}>{title(c.category)}</option>)}</select></Field><Field label="Monthly limit (VND)"><input name="amount" type="number" required min={1000} max={1000000000} step={1000} defaultValue={editing?.amount_vnd} /></Field><button className="primary-button" disabled={op.busy}>Save budget<ArrowUpRight size={16} /></button></form></div></Sheet>
    </>}
  </div>;
}