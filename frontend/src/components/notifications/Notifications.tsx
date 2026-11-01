import { useEffect, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Bell } from 'lucide-react';
import { api } from '../../api';
import type { DemoUser, NotificationPage } from '../../types';
import { recordedTime } from '../activity/TransactionDetails';
import { Pagination } from '../ui/Pagination';

export function Notifications({ user, openTransaction }: { user: DemoUser; openTransaction: (id: string) => void }) {
  const [data, setData] = useState<NotificationPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(true);
  const [changing, setChanging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') setRevision(n => n + 1);
    }, 15_000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError(null);
    api.notifications(user, offset).then(result => { if (active) setData(result); })
      .catch(err => { if (active) setError(err.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [user, offset, revision]);
  async function read(id?: string) {
    if (changing) return;
    setChanging(true);
    setError(null);
    try {
      if (id) {
        const result = await api.readNotification(user, id);
        setData(previous => previous && ({ ...previous, unread_count: Math.max(0, previous.unread_count - (previous.items.find(n => n.id === id)?.read_at ? 0 : 1)),
          items: previous.items.map(n => n.id === id ? result : n) }));
      } else {
        await api.readAllNotifications(user);
        setRevision(n => n + 1);
      }
    } catch (err) { setError((err as Error).message); }
    finally { setChanging(false); }
  }
  return <div className="page">
    <div className="page-heading"><div><h1 className="page-title">Alerts</h1><p className="muted">Updates about your money, in one place.</p></div>
      <button className="secondary-button" disabled={busy || changing} onClick={() => setRevision(n => n + 1)}>Refresh</button></div>
    {error && <div className="form-error" role="alert">{error} <button className="link-button" onClick={() => setRevision(n => n + 1)}>Try again</button></div>}
    {busy && <p className="muted" role="status">Loading alerts…</p>}
    {data && <>
      <div className="page-heading"><span className="muted" role="status">{data.unread_count} unread</span>
        <button className="link-button" disabled={changing || busy || data.unread_count === 0} onClick={() => read()}>Mark all as read</button></div>
      {data.total === 0 ? <section className="card empty-state"><Bell size={28} aria-hidden="true" /><h2>You’re all caught up</h2><p className="muted">Transfer updates will appear here.</p></section> :
        <ul className="notification-list">{data.items.map(n => <li className="card notification" key={n.id} data-unread={!n.read_at}>
          <span className={`tx-icon ${n.kind === 'MONEY_IN' ? 'in' : 'out'}`} aria-hidden="true">{n.kind === 'MONEY_IN' ? <ArrowDownLeft size={20} /> : <ArrowUpRight size={20} />}</span>
          <div className="notification-content"><h2>{n.title} {!n.read_at && <span className="unread-label">Unread</span>}</h2>
            <p>{n.body}</p><time className="muted small" dateTime={n.created_at}>{recordedTime(n.created_at)} · Vietnam</time>
            <div className="inline-actions">{n.transaction_id && <button className="link-button" onClick={() => { void read(n.id); openTransaction(n.transaction_id!); }}>View transaction</button>}
              {!n.read_at && <button className="link-button" disabled={changing || busy} onClick={() => read(n.id)}>Mark as read</button>}</div>
          </div>
        </li>)}</ul>}
      <Pagination {...data} busy={busy || changing} change={setOffset} />
    </>}
  </div>;
}
