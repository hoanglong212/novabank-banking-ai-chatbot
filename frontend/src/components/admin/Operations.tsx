import { useEffect, useState } from 'react';
import { api } from '../../api';
import { vnd } from '../../format';
import type { AuditEvent, DemoUser, Transaction } from '../../types';
import { useTransactionPage } from '../../hooks/useTransactionPage';
import { TransactionFilters } from '../activity/TransactionFilters';
import { recordedTime, TransactionInfo } from '../activity/TransactionDetails';
import { Pagination } from '../ui/Pagination';
import { Sheet } from '../ui/Sheet';

function AuditTrail({ user, id }: { user: DemoUser; id: string }) {
  const [items, setItems] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setError(null);
    api.transferAudit(user, id).then(result => { if (active) setItems(result.items); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [user, id, attempt]);
  return <section className="audit-section"><h3>Audit trail</h3><p className="muted small">{id}</p>
    {error ? <div className="form-error" role="alert">{error} <button className="link-button" onClick={() => setAttempt(n => n + 1)}>Try again</button></div> : !items ? <p role="status">Loading audit trail…</p> :
      <ol className="audit-list">{items.map(event => <li key={event.id}>
        <strong>{event.action.replaceAll('_', ' ')}</strong><span>{event.reason_code.replaceAll('_', ' ')}</span>
        <small className="muted">{event.owner_id} · {recordedTime(event.created_at)}</small>
        {event.before_balance_vnd != null && <small>Balance: {vnd(event.before_balance_vnd)} → {vnd(event.after_balance_vnd ?? event.before_balance_vnd)}</small>}
      </li>)}</ol>}
  </section>;
}

export function Operations({ user }: { user: DemoUser }) {
  const page = useTransactionPage(user, true);
  const [selected, setSelected] = useState<Transaction | null>(null);
  return <div className="page">
    <div><h1 className="page-title">Operations</h1><p className="muted">Review customer transactions and their audit trail.</p></div>
    <TransactionFilters apply={page.apply} busy={page.busy} />
    {page.error ? <div className="form-error" role="alert">{page.error} <button className="link-button" onClick={page.retry}>Try again</button></div> : <>
      {page.busy && <p className="muted" role="status">Loading transactions…</p>}
      <div className="card operations-table" tabIndex={0} role="region" aria-label="Transactions table">
        <table><thead><tr><th>Reference / description</th><th>Account</th><th>Amount</th><th>Status</th><th><span className="sr-only">Details</span></th></tr></thead>
          <tbody>{page.data.items.map(t => <tr key={t.id}><td><strong>{t.id}</strong><small>{t.description}</small></td><td>{t.account_id}<small>{t.holder_name}</small></td>
            <td className={t.direction}>{t.direction === 'in' ? '+' : '-'}{vnd(t.amount_vnd)}</td><td><span className={`badge badge-${t.status.toLowerCase()}`}>{t.status.toLowerCase()}</span></td>
            <td><button className="secondary-button" disabled={page.busy} onClick={() => setSelected(t)}>View details<span className="sr-only"> {t.id}</span></button></td></tr>)}</tbody>
        </table>
        {!page.busy && page.data.total === 0 && <p className="muted">No matching transactions.</p>}
      </div><Pagination {...page.data} busy={page.busy} change={page.move} />
    </>}
    <Sheet open={selected !== null} onClose={() => setSelected(null)} title="Transaction review">
      {selected && <><TransactionInfo transaction={selected} />
        {selected.transfer_id ? <AuditTrail key={selected.transfer_id} user={user} id={selected.transfer_id} /> : <p className="muted">No transfer audit is recorded for this older transaction.</p>}
      </>}
    </Sheet>
  </div>;
}
