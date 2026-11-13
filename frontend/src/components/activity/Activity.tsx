import { useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, ChevronRight, ReceiptText } from 'lucide-react';

import type { DemoUser, Profile, Transaction } from '../../types';
import { vnd } from '../../format';
import { TransactionFilters } from './TransactionFilters';
import { Pagination } from '../ui/Pagination';
import { useTransactionPage } from '../../hooks/useTransactionPage';
import { MonthPulse, SafetyTip, StatementShortcut, UpcomingBills } from '../home/Rail';

interface ActivityProps {
  user: DemoUser;
  profile: Profile | null;
  openTransaction: (id: string) => void;
}

const FILTERS = [['all', 'All'], ['in', 'Money in'], ['out', 'Money out']] as const;
const ZONE = 'Asia/Ho_Chi_Minh';
const signed = (amount: number) => (amount >= 0 ? '+' : '-') + vnd(Math.abs(amount));
const clock = (iso?: string) => iso ? new Date(iso).toLocaleTimeString('en-GB', { timeZone: ZONE, hour: '2-digit', minute: '2-digit' }) : '';

function dayLabel(date: string) {
  const today = new Date().toLocaleDateString('sv-SE', { timeZone: ZONE });
  const yesterday = new Date(Date.now() - 86_400_000).toLocaleDateString('sv-SE', { timeZone: ZONE });
  if (date === today) return 'Today';
  if (date === yesterday) return 'Yesterday';
  return new Date(date + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long' });
}
const monthDay = (date: string) => new Date(date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long' });

// Only completed money counts toward totals; pending and failed rows are shown but not summed.
const sum = (items: Transaction[], direction: 'in' | 'out') =>
  items.filter(t => t.status === 'COMPLETED' && t.direction === direction).reduce((total, t) => total + t.amount_vnd, 0);

export function MonthCard({ profile }: { profile: Profile | null }) {
  const total = (direction: 'in' | 'out') =>
    (profile?.transactions ?? []).filter(t => t.direction === direction && t.status === 'COMPLETED').reduce((sum, t) => sum + t.amount_vnd, 0);
  const moneyIn = total('in'), moneyOut = total('out');
  const share = moneyIn + moneyOut ? Math.round(moneyIn / (moneyIn + moneyOut) * 100) : 50;
  return (
    <section className="card month-card" aria-label="Completed activity">
      <div className="month-head">
        <span>Completed activity</span>
        <small>Recent posted transactions</small>
      </div>
      {profile ? <>
        <div className="month-net"><small>Net cash flow</small><strong>{signed(moneyIn - moneyOut)}</strong></div>
        <div className="flow-bar" role="img" aria-label={`${share}% of money moved was money in`}><span style={{ width: share + '%' }} /></div>
        <div className="month-totals">
          <div><span className="flow-icon in" aria-hidden="true"><ArrowDownLeft size={16} /></span><small>Money in</small><strong>+{vnd(moneyIn)}</strong></div>
          <div><span className="flow-icon out" aria-hidden="true"><ArrowUpRight size={16} /></span><small>Money out</small><strong>-{vnd(moneyOut)}</strong></div>
        </div>
      </> : <div className="month-totals"><span className="skeleton skeleton-text" /><span className="skeleton skeleton-text" /></div>}
    </section>
  );
}

export function Activity({ user, profile, openTransaction }: ActivityProps) {
  const [filter, setFilter] = useState<'all' | 'in' | 'out'>('all');
  const page = useTransactionPage(user, false, profile?.transactions);
  const shown = page.data.items;
  const days = [...new Set(shown.map(t => t.date))];

  return (
    <div className="page activity with-rail">
      <div className="rail-main">
      <div className="page-heading">
        <div><h1 className="page-title">Activity</h1><p className="muted">Every payment in and out of your accounts.</p></div>
      </div>
      <MonthCard profile={profile} />
      <TransactionFilters apply={page.apply} busy={page.busy} />
      <div className="activity-bar">
        <div className="chips segmented" role="tablist" aria-label="Filter transactions">
          {FILTERS.map(([id, label]) => (
            <button key={id} role="tab" aria-selected={filter === id} onClick={() => { setFilter(id); page.apply({ direction: id === 'all' ? '' : id }); }}>{label}</button>
          ))}
        </div>
        {!page.error && <span className="muted small" role="status">{page.busy ? 'Updating…' : `${page.data.total} transaction${page.data.total === 1 ? '' : 's'}`}</span>}
      </div>
      {page.error ? <div className="form-error" role="alert">{page.error} <button className="link-button" onClick={page.retry}>Try again</button></div> : page.busy && shown.length === 0 ? (
        <section className="card">{[0, 1, 2, 3].map(i => <div key={i} className="skeleton skeleton-row" />)}</section>
      ) : shown.length === 0 ? (
        <section className="card empty-state"><ReceiptText size={28} aria-hidden="true" /><h2>No transactions found</h2><p className="muted">Try another search, date range or status.</p></section>
      ) : days.map(day => {
        const items = shown.filter(t => t.date === day);
        const moneyIn = sum(items, 'in'), moneyOut = sum(items, 'out'), dayNet = moneyIn - moneyOut;
        const tone = dayNet > 0 ? 'in' : dayNet < 0 ? 'out' : 'flat';
        return <section key={day} className="day-group" aria-label={`${dayLabel(day)} ${monthDay(day)}`}>
          <div className="day-head">
            <span className="day-badge" aria-hidden="true"><b>{Number(day.slice(8))}</b><small>{new Date(day + 'T00:00:00').toLocaleDateString('en-GB', { month: 'short' })}</small></span>
            <div className="day-title">
              <h2 className="day-label">{dayLabel(day)}</h2>
              <small>{monthDay(day)} · {items.length} transaction{items.length === 1 ? '' : 's'}</small>
            </div>
            <div className={`day-net is-${tone}`}>
              <small>Day total</small>
              <strong>{signed(dayNet)}</strong>
              <span className="day-split">
                {moneyIn > 0 && <span className="in"><ArrowDownLeft size={12} aria-hidden="true" />{vnd(moneyIn)}</span>}
                {moneyOut > 0 && <span className="out"><ArrowUpRight size={12} aria-hidden="true" />{vnd(moneyOut)}</span>}
              </span>
            </div>
          </div>
          <ul className="card tx-list">
            {items.map(t => (
              <li key={t.id}>
                <button className="tx" disabled={page.busy} onClick={() => openTransaction(t.id)}>
                  <span className={`tx-icon ${t.direction}`} aria-hidden="true">{t.direction === 'in' ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</span>
                  <span className="tx-main">
                    <strong>{t.description}</strong>
                    <small>{clock(t.created_at) && <>{clock(t.created_at)} · </>}<span className="tx-ref">{t.id}</span></small>
                  </span>
                  <span className="tx-side">
                    <span className={`tx-amount ${t.direction}`}>{t.direction === 'in' ? '+' : '-'}{vnd(t.amount_vnd)}</span>
                    {t.status !== 'COMPLETED' && <span className={`badge badge-${t.status.toLowerCase()}`}>{t.status.toLowerCase()}</span>}
                  </span>
                  <ChevronRight className="tx-chevron" size={18} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        </section>;
      })}

      {!page.error && <Pagination {...page.data} busy={page.busy} change={page.move} />}
      </div>
      <aside className="side-rail" aria-label="At a glance">
        <MonthPulse user={user} />
        <UpcomingBills user={user} />
        <StatementShortcut />
        <SafetyTip />
      </aside>
    </div>
  );
}
