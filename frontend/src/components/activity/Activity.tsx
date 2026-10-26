import { useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, MessageCircle } from 'lucide-react';

import type { Profile, Transaction } from '../../types';
import { vnd } from '../../format';
import { Sheet } from '../ui/Sheet';

interface ActivityProps {
  profile: Profile | null;
  ask: (text: string) => void;
}

const FILTERS = [['all', 'All'], ['in', 'Money in'], ['out', 'Money out']] as const;

function dayLabel(date: string) {
  return new Date(date + 'T00:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function Activity({ profile, ask }: ActivityProps) {
  const [filter, setFilter] = useState<'all' | 'in' | 'out'>('all');
  const [selected, setSelected] = useState<Transaction | null>(null);
  const all = profile?.transactions ?? [];
  const shown = all.filter(t => filter === 'all' || t.direction === filter);
  const total = (direction: 'in' | 'out') => all.filter(t => t.direction === direction).reduce((sum, t) => sum + t.amount_vnd, 0);
  const days = [...new Set(shown.map(t => t.date))];

  return (
    <div className="page">
      <h1 className="page-title">Activity</h1>
      <section className="card month-card">
        <span className="muted">This month</span>
        <div className="month-totals">
          <div><small>Money in</small><strong className="in">+{vnd(total('in'))}</strong></div>
          <div><small>Money out</small><strong>-{vnd(total('out'))}</strong></div>
        </div>
      </section>
      <div className="chips" role="tablist" aria-label="Filter transactions">
        {FILTERS.map(([id, label]) => (
          <button key={id} role="tab" aria-selected={filter === id} onClick={() => setFilter(id)}>{label}</button>
        ))}
      </div>
      {profile === null ? (
        <section className="card">{[0, 1, 2, 3].map(i => <div key={i} className="skeleton skeleton-row" />)}</section>
      ) : shown.length === 0 ? <p className="muted">No transactions.</p> : days.map(day => (
        <section key={day} className="day-group">
          <h2 className="day-label">{dayLabel(day)}</h2>
          <ul className="card tx-list">
            {shown.filter(t => t.date === day).map(t => (
              <li key={t.id}>
                <button className="tx" onClick={() => setSelected(t)}>
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

      <Sheet open={selected !== null} onClose={() => setSelected(null)} title="Transaction details">
        {selected && (
          <div className="tx-detail">
            <span className={`tx-icon tx-icon-lg ${selected.direction}`}>{selected.direction === 'in' ? <ArrowDownLeft size={26} /> : <ArrowUpRight size={26} />}</span>
            <strong className={`tx-detail-amount ${selected.direction}`}>{selected.direction === 'in' ? '+' : '-'}{vnd(selected.amount_vnd)}</strong>
            <span className={`badge badge-${selected.status.toLowerCase()}`}>{selected.status.toLowerCase()}</span>
            <dl className="detail-list">
              <div><dt>Description</dt><dd>{selected.description}</dd></div>
              <div><dt>Date</dt><dd>{dayLabel(selected.date)}</dd></div>
              <div><dt>Reference</dt><dd>{selected.id}</dd></div>
              <div><dt>Type</dt><dd>{selected.direction === 'in' ? 'Incoming' : 'Outgoing'}</dd></div>
            </dl>
            <button className="secondary-button" onClick={() => { const id = selected.id; setSelected(null); ask(`Check transaction ${id}`); }}>
              <MessageCircle size={18} aria-hidden="true" /> Ask Nova about this
            </button>
          </div>
        )}
      </Sheet>
    </div>
  );
}
