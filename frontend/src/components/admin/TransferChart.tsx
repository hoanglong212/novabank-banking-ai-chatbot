import { useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { vnd } from '../../format';
import { shortDay, count, type TransferDay } from './dashboardTypes';

const compact = (value: number) => new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
export function TransferChart({ days }: { days: TransferDay[] }) {
  const [selected, setSelected] = useState(days.length - 1);
  const peak = Math.max(0, ...days.map(day => day.internal_vnd + day.external_vnd));
  const active = days[Math.min(selected, days.length - 1)];
  const interval = Math.max(1, Math.ceil(days.length / 7));
  return <div className="admin-chart">
    <div className="admin-chart-legend"><span><i />NovaBank</span><span><i />Other banks</span><small>Settled principal · VND</small></div>
    {peak ? <><div className="admin-chart-area"><div className="admin-chart-scale" aria-hidden="true"><span>{compact(peak)}</span><span>{compact(peak / 2)}</span><span>0</span></div><div className="admin-chart-plot">
      <div className="admin-chart-rules" aria-hidden="true"><i /><i /><i /></div><div className="admin-chart-columns">{days.map((day, i) => <button key={day.date} className={`admin-chart-bar${i === selected ? ' is-selected' : ''}`} aria-pressed={i === selected} aria-label={`${shortDay(day.date)}: ${vnd(day.internal_vnd + day.external_vnd)}, ${day.completed} completed transfers`} onFocus={() => setSelected(i)} onMouseEnter={() => setSelected(i)} onClick={() => setSelected(i)}><span className="admin-bar-stack" style={{ height: `${Math.max(1, (day.internal_vnd + day.external_vnd) / peak * 100)}%` }}><span style={{ flexGrow: day.internal_vnd }} /><span style={{ flexGrow: day.external_vnd }} /></span></button>)}</div>
    </div></div><div className="admin-chart-dates" aria-hidden="true">{days.map((day, i) => <span key={day.date}>{i % interval === 0 || i === days.length - 1 ? shortDay(day.date) : ''}</span>)}</div><div className="admin-chart-selection" aria-live="polite"><strong>{shortDay(active.date)}</strong><span>{vnd(active.internal_vnd + active.external_vnd)}</span><small>Completed: {count(active.completed)}</small></div></> : <div className="admin-chart-empty"><BarChart3 size={32} strokeWidth={1.4} /><strong>No settled transfers in this period</strong><p>Completed transfers will build this chart. Try a longer period to see earlier activity.</p></div>}
    <details className="admin-chart-data"><summary>View daily figures</summary><div className="admin-table-scroll" tabIndex={0} role="region" aria-label="Daily transfer figures"><table><thead><tr><th>Date</th><th>NovaBank</th><th>Other banks</th><th>Completed</th></tr></thead><tbody>{days.map(day => <tr key={day.date}><td>{shortDay(day.date)}</td><td>{vnd(day.internal_vnd)}</td><td>{vnd(day.external_vnd)}</td><td>{count(day.completed)}</td></tr>)}</tbody></table></div></details>
  </div>;
}
