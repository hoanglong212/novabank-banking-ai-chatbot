import { useState, type FormEvent } from 'react';
import type { TransactionFilters as Filters } from '../../types';

export function TransactionFilters({ apply, busy }: { apply: (filters: Filters) => void; busy: boolean }) {
  const [q, setQ] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [status, setStatus] = useState<Filters['status']>('');
  function submit(event: FormEvent) {
    event.preventDefault();
    apply({ q: q.trim(), from_date: from, to_date: to, status });
  }
  return <form className="card history-filters" onSubmit={submit} aria-label="Search transactions">
    <label className="field search-field"><span>Search</span><input type="search" placeholder="Reference, account or description" maxLength={100} value={q} onChange={e => setQ(e.target.value)} /></label>
    <label className="field"><span>From date</span><input type="date" value={from} max={to || undefined} onChange={e => setFrom(e.target.value)} /></label>
    <label className="field"><span>To date</span><input type="date" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} /></label>
    <label className="field"><span>Status</span><select value={status} onChange={e => setStatus(e.target.value as Filters['status'])}>
      <option value="">All statuses</option><option value="COMPLETED">Completed</option><option value="PENDING">Pending</option><option value="FAILED">Failed</option>
    </select></label>
    <button className="secondary-button" disabled={busy} type="submit">Search transactions</button>
  </form>;
}
