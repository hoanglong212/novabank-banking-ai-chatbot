import { useState } from 'react';
import { ArrowDownLeft, ArrowUpRight } from 'lucide-react';

import type { DemoUser, Profile } from '../../types';
import { vnd } from '../../format';
import { TransactionFilters } from './TransactionFilters';
import { Pagination } from '../ui/Pagination';
import { useTransactionPage } from '../../hooks/useTransactionPage';

interface ActivityProps {
  user: DemoUser;
  profile: Profile | null;
  openTransaction: (id: string) => void;
}

const FILTERS = [['all', 'All'], ['in', 'Money in'], ['out', 'Money out']] as const;

function dayLabel(date: string) {
  return new Date(date + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function MonthCard({ profile }: { profile: Profile | null }) {
  const total = (direction: 'in' | 'out') =>
    (profile?.transactions ?? []).filter(t => t.direction === direction && t.status === 'COMPLETED').reduce((sum, t) => sum + t.amount_vnd, 0);
  return (
    <section className="card month-card">
      <span className="muted">Completed activity</span>
      <div className="month-totals">
        {profile ? <>
          <div><small>Money in</small><strong className="in">+{vnd(total('in'))}</strong></div>
          <div><small>Money out</small><strong>-{vnd(total('out'))}</strong></div>
        </> : <><span className="skeleton skeleton-text" /><span className="skeleton skeleton-text" /></>}
      </div>
    </section>
  );
}

export function Activity({ user, profile, openTransaction }: ActivityProps) {
  const [filter, setFilter] = useState<'all' | 'in' | 'out'>('all');
  const page = useTransactionPage(user, false, profile?.transactions);
  const shown = page.data.items;
  const days = [...new Set(shown.map(t => t.date))];

  return (
    <div className="page">
      <h1 className="page-title">Activity</h1>
      <MonthCard profile={profile} />
      <TransactionFilters apply={page.apply} busy={page.busy} />
      <div className="chips" role="tablist" aria-label="Filter transactions">
        {FILTERS.map(([id, label]) => (
          <button key={id} role="tab" aria-selected={filter === id} onClick={() => { setFilter(id); page.apply({ direction: id === 'all' ? '' : id }); }}>{label}</button>
        ))}
      </div>
      {page.error ? <div className="form-error" role="alert">{page.error} <button className="link-button" onClick={page.retry}>Try again</button></div> : page.busy && shown.length === 0 ? (
        <section className="card">{[0, 1, 2, 3].map(i => <div key={i} className="skeleton skeleton-row" />)}</section>
      ) : shown.length === 0 ? <p className="muted">No transactions.</p> : days.map(day => (
        <section key={day} className="day-group">
          <h2 className="day-label">{dayLabel(day)}</h2>
          <ul className="card tx-list">
            {shown.filter(t => t.date === day).map(t => (
              <li key={t.id}>
                <button className="tx" disabled={page.busy} onClick={() => openTransaction(t.id)}>
                  <span className={`tx-icon ${t.direction}`}>{t.direction === 'in' ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</span>
                  <span className="tx-main">
                    <strong>{t.description}</strong>
                    <small>{t.id}{t.status !== 'COMPLETED' && <span className={`badge badge-${t.status.toLowerCase()}`}>{t.status.toLowerCase()}</span>}</small>
                  </span>
                  <span className={`tx-amount ${t.direction}`}>{t.direction === 'in' ? '+' : '-'}{vnd(t.amount_vnd)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {page.busy && <span className="muted" role="status">Updating transactions…</span>}
      {!page.error && <Pagination {...page.data} busy={page.busy} change={page.move} />}
    </div>
  );
}
