import { useId, useState, type FormEvent } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Search, SlidersHorizontal, X } from 'lucide-react';
import type { TransactionFilters as Filters } from '../../types';

// Dates stay as YYYY-MM-DD strings so they compare lexically and match the API.
const iso = (date: Date) => date.toLocaleDateString('sv-SE');
const parse = (day: string) => new Date(day + 'T12:00:00');
const shift = (day: string, days: number) => iso(new Date(parse(day).getTime() + days * 86_400_000));
const short = (day: string) => parse(day).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const WEEK = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
const STATUSES = [['', 'All'], ['COMPLETED', 'Completed'], ['PENDING', 'Pending'], ['FAILED', 'Failed']] as const;

function presets(today: string): [string, string, string][] {
  const t = parse(today);
  const first = iso(new Date(t.getFullYear(), t.getMonth(), 1));
  const lastStart = iso(new Date(t.getFullYear(), t.getMonth() - 1, 1));
  const lastEnd = iso(new Date(t.getFullYear(), t.getMonth(), 0));
  return [['Today', today, today], ['7 days', shift(today, -6), today], ['30 days', shift(today, -29), today],
    ['This month', first, today], ['Last month', lastStart, lastEnd]];
}

/** Next range after tapping `day`: first tap starts a range, second tap closes it (swapping if earlier). */
export function pickRange(from: string, to: string, day: string): [string, string] {
  if (!from || to) return [day, ''];
  return day < from ? [day, from] : [from, day];
}

function Calendar({ from, to, pick, today }: { from: string; to: string; pick: (day: string) => void; today: string }) {
  const [view, setView] = useState(() => (to || from || today).slice(0, 7));
  const [y, m] = view.split('-').map(Number);
  const lead = (new Date(y, m - 1, 1).getDay() + 6) % 7;
  const count = new Date(y, m, 0).getDate();
  const move = (step: number) => setView(iso(new Date(y, m - 1 + step, 1)).slice(0, 7));
  const days = Array.from({ length: count }, (_, i) => `${view}-${String(i + 1).padStart(2, '0')}`);
  const end = to || from;
  return <div className="calendar">
    <div className="calendar-head">
      <button type="button" className="icon-button" aria-label="Previous month" onClick={() => move(-1)}><ChevronLeft size={18} /></button>
      <strong aria-live="polite">{new Date(y, m - 1, 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</strong>
      <button type="button" className="icon-button" aria-label="Next month" disabled={view >= today.slice(0, 7)} onClick={() => move(1)}><ChevronRight size={18} /></button>
    </div>
    <div className="calendar-grid" role="group" aria-label="Choose dates">
      {WEEK.map(d => <span key={d} className="calendar-week" aria-hidden="true">{d}</span>)}
      {Array.from({ length: lead }, (_, i) => <span key={'x' + i} />)}
      {days.map(day => {
        const edge = day === from || day === end;
        const inside = !!from && day > from && day < end;
        return <button type="button" key={day} disabled={day > today} onClick={() => pick(day)}
          className={['calendar-day', edge && 'is-edge', inside && 'is-inside', day === from && to && to !== from && 'is-start', day === to && to !== from && 'is-end', day === today && 'is-today'].filter(Boolean).join(' ')}
          aria-pressed={edge || inside} aria-label={parse(day).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}>
          <span>{Number(day.slice(8))}</span>
        </button>;
      })}
    </div>
  </div>;
}

export function TransactionFilters({ apply, busy }: { apply: (filters: Filters) => void; busy: boolean }) {
  const [q, setQ] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [status, setStatus] = useState<Filters['status']>('');
  const [open, setOpen] = useState(false);
  const panel = useId();
  const today = iso(new Date());
  const active = [from, status].filter(Boolean).length;
  const range = from ? (to && to !== from ? `${short(from)} – ${short(to)}` : to ? short(from) : `From ${short(from)}`) : 'Any date';
  function submit(event: FormEvent) {
    event.preventDefault();
    apply({ q: q.trim(), from_date: from, to_date: to, status });
  }
  function reset() {
    setQ(''); setFrom(''); setTo(''); setStatus('');
    apply({ q: '', from_date: '', to_date: '', status: '' });
  }
  return <form className="history-filters" onSubmit={submit} aria-label="Search transactions">
    <div className="history-bar">
      <label className="alerts-search">
        <Search size={18} aria-hidden="true" /><span className="sr-only">Search</span>
        <input type="search" placeholder="Reference, account or description" maxLength={100} value={q} onChange={e => setQ(e.target.value)} />
        {q && <button type="button" className="icon-button" aria-label="Clear search" onClick={() => setQ('')}><X size={16} /></button>}
      </label>
      <button type="button" className="filter-chip" aria-expanded={open} aria-controls={panel} onClick={() => setOpen(v => !v)}>
        <SlidersHorizontal size={16} aria-hidden="true" /><span className="filter-label">Filters</span>
        {active > 0 && <span className="tab-count" aria-label={`${active} active`}>{active}</span>}
      </button>
      <button className="primary-button history-submit" disabled={busy} type="submit">Search<span className="sr-only"> transactions</span></button>
    </div>
    {open && <div className="card history-more" id={panel}>
      <div className="range-summary">
        <span className="range-icon" aria-hidden="true"><CalendarDays size={20} /></span>
        <div><small>Date range</small><strong aria-live="polite">{range}</strong></div>
        {from && <button type="button" className="link-button" onClick={() => { setFrom(''); setTo(''); }}>Clear dates</button>}
      </div>
      <div className="preset-row" role="group" aria-label="Quick date range">
        {presets(today).map(([label, a, b]) => (
          <button type="button" key={label} className="preset" aria-pressed={from === a && to === b} onClick={() => { setFrom(a); setTo(b); }}>{label}</button>
        ))}
      </div>
      <Calendar key={to || from || 'none'} from={from} to={to} today={today} pick={day => { const [a, b] = pickRange(from, to, day); setFrom(a); setTo(b); }} />
      <div className="status-row" role="group" aria-label="Status">
        {STATUSES.map(([value, label]) => (
          <button type="button" key={label} className={`status-pill status-${(value || 'all').toLowerCase()}`} aria-pressed={status === value} onClick={() => setStatus(value)}>
            <span className="pill-dot" aria-hidden="true" />{label}
          </button>
        ))}
      </div>
      <div className="history-more-actions">
        <button type="button" className="link-button" onClick={reset}>Reset all</button>
        <button type="submit" className="primary-button" disabled={busy}>Apply filters</button>
      </div>
    </div>}
  </form>;
}
