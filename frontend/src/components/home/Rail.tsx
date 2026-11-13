import { useEffect, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, CalendarClock, ChevronRight, FileDown, Lightbulb, Megaphone, ShieldCheck } from 'lucide-react';
import { api } from '../../api';
import type { Announcement, DemoUser } from '../../types';
import { vnd } from '../../format';
import { navigate } from '../../router';
import { useResource } from '../explore/shared';

// Desktop side rail: small, real-data cards that fill wide screens. Hidden below 1200px by CSS.
const ZONE = 'Asia/Ho_Chi_Minh';
const thisMonth = () => new Date().toLocaleDateString('sv-SE', { timeZone: ZONE }).slice(0, 7);
const short = (iso: string) => new Date(iso + (iso.length === 10 ? 'T12:00:00+07:00' : '')).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

// Calendar days from today in Vietnam; negative means overdue.
function dueIn(day: string) {
  const days = Math.round((Date.parse(day + 'T00:00:00+07:00') - Date.parse(new Date().toLocaleDateString('sv-SE', { timeZone: ZONE }) + 'T00:00:00+07:00')) / 86_400_000);
  return days < 0 ? `Overdue by ${-days} day${days === -1 ? '' : 's'}` : days === 0 ? 'Due today' : days === 1 ? 'Due tomorrow' : `Due in ${days} days`;
}

interface Insights { income_vnd: number; expense_vnd: number; categories: { category: string; amount_vnd: number }[]; previous?: { expense_vnd: number } }
interface Bill { id: string; provider: string; amount_vnd: number; due_date: string; status: string }

export function MonthPulse({ user }: { user: DemoUser }) {
  const month = thisMonth();
  const data = useResource<Insights>(user, `/insights?month=${month}`).data;
  const top = (data?.categories ?? []).filter(c => c.amount_vnd > 0).sort((a, b) => b.amount_vnd - a.amount_vnd).slice(0, 3);
  const max = top[0]?.amount_vnd || 1;
  const change = data?.previous?.expense_vnd ? Math.round((data.expense_vnd / data.previous.expense_vnd - 1) * 100) : null;
  return <section className="card rail-card" aria-label="This month">
    <header className="rail-head"><h2>This month</h2><button className="link-button" onClick={() => navigate('/explore/insights')}>Details <ChevronRight size={14} aria-hidden="true" /></button></header>
    {!data ? <><span className="skeleton skeleton-text" /><span className="skeleton skeleton-row" /></> : <>
      <div className="rail-flow">
        <div><span className="rail-dot in"><ArrowDownLeft size={13} aria-hidden="true" /></span><small>In</small><strong>{vnd(data.income_vnd)}</strong></div>
        <div><span className="rail-dot out"><ArrowUpRight size={13} aria-hidden="true" /></span><small>Out</small><strong>{vnd(data.expense_vnd)}</strong></div>
      </div>
      {change !== null && <p className="rail-note">{change === 0 ? 'Spending is level with last month.' : `Spending is ${Math.abs(change)}% ${change > 0 ? 'higher' : 'lower'} than last month.`}</p>}
      {top.length > 0 && <ul className="rail-bars">{top.map(c => <li key={c.category}>
        <span>{c.category}</span><strong>{vnd(c.amount_vnd)}</strong>
        <i aria-hidden="true"><b style={{ width: `${Math.max(6, c.amount_vnd / max * 100)}%` }} /></i>
      </li>)}</ul>}
    </>}
  </section>;
}

export function UpcomingBills({ user }: { user: DemoUser }) {
  const data = useResource<{ items: Bill[] }>(user, '/products/bills').data;
  const due = (data?.items ?? []).filter(b => b.status === 'UNPAID').sort((a, b) => a.due_date.localeCompare(b.due_date)).slice(0, 3);
  return <section className="card rail-card" aria-label="Upcoming bills">
    <header className="rail-head"><h2>Upcoming bills</h2><button className="link-button" onClick={() => navigate('/explore/bills')}>Pay <ChevronRight size={14} aria-hidden="true" /></button></header>
    {!data ? <span className="skeleton skeleton-row" /> : due.length === 0
      ? <p className="rail-empty"><CalendarClock size={18} aria-hidden="true" />Nothing due. You are all paid up.</p>
      : <ul className="rail-list">{due.map(b => <li key={b.id}>
        <span className="rail-date"><b>{short(b.due_date).split(' ')[0]}</b>{short(b.due_date).split(' ')[1]}</span>
        <span className="rail-main"><strong>{b.provider}</strong><small>{dueIn(b.due_date)}</small></span>
        <strong className="rail-amount">{vnd(b.amount_vnd)}</strong>
      </li>)}</ul>}
  </section>;
}

export function NewsTeaser({ user }: { user: DemoUser }) {
  const [item, setItem] = useState<Announcement | null>(null);
  useEffect(() => { api.announcements(user).then(r => setItem(r.items.find(n => n.kind === 'CAMPAIGN') ?? r.items[0] ?? null)).catch(() => { }); }, [user]);
  if (!item) return null;
  return <section className="card rail-card rail-promo" aria-label="From NovaBank">
    <span className="rail-promo-tag"><Megaphone size={14} aria-hidden="true" />{item.tag}</span>
    <h2>{item.title}</h2>
    <p>{item.body}</p>
    {item.action_path && <button className="rail-promo-cta" onClick={() => navigate(item.action_path!)}>{item.action_label ?? 'Learn more'} <ChevronRight size={15} aria-hidden="true" /></button>}
  </section>;
}

const TIPS = [
  'NovaBank never asks for your OTP, PIN or password, not even through Nova.',
  'Check the recipient name before confirming any transfer.',
  'Scan only QR codes you trust. Nova shows the details before you pay.',
  'Sign out on shared devices and review your sessions in Profile.',
];
export function SafetyTip() {
  // Same tip all day, a different one tomorrow.
  const tip = TIPS[Math.floor(Date.now() / 86_400_000) % TIPS.length];
  return <section className="card rail-card rail-tip" aria-label="Safety tip">
    <span className="rail-tip-icon" aria-hidden="true"><ShieldCheck size={18} /></span>
    <div><h2>Stay safe</h2><p>{tip}</p></div>
  </section>;
}

export function StatementShortcut() {
  return <button className="card rail-card rail-link" onClick={() => navigate('/explore/statements')}>
    <span className="rail-tip-icon" aria-hidden="true"><FileDown size={18} /></span>
    <span><strong>Download a statement</strong><small>PDF for any date range</small></span>
    <ChevronRight size={18} aria-hidden="true" />
  </button>;
}

export function HelpShortcut({ ask }: { ask: (text: string) => void }) {
  return <button className="card rail-card rail-link" onClick={() => ask('Summarise my spending this month')}>
    <span className="rail-tip-icon" aria-hidden="true"><Lightbulb size={18} /></span>
    <span><strong>Ask Nova</strong><small>“Summarise my spending this month”</small></span>
    <ChevronRight size={18} aria-hidden="true" />
  </button>;
}
