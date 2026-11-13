import { useState } from 'react';
import { Download, FileText } from 'lucide-react';
import type { DemoUser } from '../../types';
import { download, Feedback, Field, useOperation } from './shared';
import { ServiceHeading, ServiceNote, today, displayDate } from './ServiceUi';

export function Statements({ user }: { user: DemoUser }) {
  const now = today();
  const [from, setFrom] = useState(now.slice(0, 8) + '01'), [to, setTo] = useState(now), [format, setFormat] = useState('pdf');
  const op = useOperation();
  const days = (Date.parse(to) - Date.parse(from)) / 86400000;
  const valid = !!from && !!to && days >= 0 && days <= 366;
  function period(months: number) { const date = new Date(now + 'T12:00:00'); date.setMonth(date.getMonth() - months + 1, 1); setFrom(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-01`); setTo(now); }
  return <div className="service-stack"><ServiceHeading eyebrow="YOUR RECORDS, READY WHEN YOU ARE" title="A clearer view of your account">Download your actual demo transactions as a PDF document or a CSV spreadsheet.</ServiceHeading><div className="service-split"><section className="card service-section"><h2 className="card-title">Download a statement</h2><div className="service-filters" aria-label="Statement period"><button onClick={() => period(1)}>This month</button><button onClick={() => period(3)}>Last 3 months</button><button onClick={() => { setFrom(now.slice(0, 4) + '-01-01'); setTo(now); }}>This year</button></div><form className="service-form" onSubmit={e => { e.preventDefault(); if (valid) void op.run(async () => { await download(user, `/statements.${format}?from_date=${from}&to_date=${to}`, `NovaBank-statement.${format}`); op.setMessage('Statement downloaded.'); }); }}>
      <div className="service-grid"><Field label="From"><input type="date" required value={from} onChange={e => setFrom(e.target.value)} /></Field><Field label="To"><input type="date" required value={to} onChange={e => setTo(e.target.value)} /></Field></div><Field label="Format"><select value={format} onChange={e => setFormat(e.target.value)}><option value="pdf">PDF document</option><option value="csv">CSV spreadsheet</option></select></Field>
      {!valid && <p role="alert" className="form-error">Choose a start date before the end date, within a period of up to one year.</p>}<button className="primary-button" disabled={op.busy || !valid}><Download size={17} />{op.busy ? 'Preparing…' : 'Download statement'}</button><Feedback state={op} />
    </form></section><aside className="statement-preview"><div className="statement-paper" aria-label="Statement format preview"><strong>NOVABANK / STATEMENT</strong><div>{user.name}<br />{valid ? `${displayDate(from)} — ${displayDate(to)}` : 'Select your dates'}</div><div className="statement-lines" aria-hidden="true"><i /><i /><i /><i /><i /></div><span>{format === 'pdf' ? 'PDF document' : 'CSV spreadsheet'} · Account activity</span></div><div className="service-note"><FileText size={20} /><span>Includes transaction references, status, fees and recorded balance snapshots. The file contains your account data only.</span></div></aside></div><ServiceNote>Statements cover up to one year. Older sample transactions may not have a recorded balance snapshot.</ServiceNote></div>;
}
