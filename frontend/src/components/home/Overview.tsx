import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { Loading, useResource } from '../explore/shared';

interface Summary { month: string; income_vnd: number; expense_vnd: number; savings_principal_vnd: number; credit_debt_vnd: number; unpaid_bills: number }
export function Overview({ user, explore, revision }: { user: DemoUser; explore: () => void; revision: number }) {
  const month = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' }).slice(0, 7);
  const state = useResource<Summary>(user, `/insights?month=${month}&revision=${revision}`);
  return <section className="card month-card"><span className="muted">This month · {month}</span><Loading state={state} />{state.data && <>
    <div className="month-totals"><div><small>Income</small><strong className="in">+{vnd(state.data.income_vnd)}</strong></div><div><small>Spending, including fees</small><strong>{vnd(state.data.expense_vnd)}</strong></div></div>
    <dl className="detail-list"><div><dt>Term savings</dt><dd>{vnd(state.data.savings_principal_vnd)}</dd></div><div><dt>Credit used</dt><dd>{vnd(state.data.credit_debt_vnd)}</dd></div><div><dt>Unpaid bills</dt><dd>{state.data.unpaid_bills}</dd></div></dl>
    <button className="link-button" onClick={explore}>Manage products and spending</button></>}</section>;
}
