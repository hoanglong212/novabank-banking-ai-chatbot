import { useEffect, useState } from 'react';
import { MessageCircle } from 'lucide-react';
import { api } from '../../api';
import { vnd } from '../../format';
import type { DemoUser, Transaction } from '../../types';
import { Sheet } from '../ui/Sheet';
import { ReceiptButton } from './ReceiptButton';
import { Feedback, Field, send, useOperation } from '../explore/shared';

export function recordedTime(value: string) {
  return new Date(value).toLocaleString('en-GB', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'medium', timeStyle: 'short' });
}

export function TransactionInfo({ transaction: t }: { transaction: Transaction }) {
  return <div className="tx-detail">
    <strong className={`tx-detail-amount ${t.direction}`}>{t.direction === 'in' ? '+' : '-'}{vnd(t.amount_vnd)}</strong>
    <span className={`badge badge-${t.status.toLowerCase()}`}>{t.status.toLowerCase()}</span>
    <dl className="detail-list">
      <div><dt>Reference</dt><dd>{t.id}</dd></div>
      <div><dt>Description</dt><dd>{t.description}</dd></div>
      <div><dt>Account</dt><dd>{t.account_id ?? 'Not recorded'}</dd></div>
      <div><dt>Date (Vietnam)</dt><dd>{t.created_at ? recordedTime(t.created_at) : t.date}</dd></div>
      {t.counterparty_account && <>
        <div><dt>{t.direction === 'in' ? 'From' : 'To'}</dt><dd>{t.counterparty_name || 'Name not verified'}</dd></div>
        <div><dt>Counterparty account</dt><dd>{t.counterparty_account}</dd></div>
        <div><dt>Bank</dt><dd>{t.counterparty_bank ?? 'NovaBank'}</dd></div>
      </>}
      <div><dt>Fee</dt><dd>{t.fee_vnd == null ? 'Not recorded' : vnd(t.fee_vnd)}</dd></div>
      <div><dt>Balance after transaction</dt><dd>{t.balance_after_vnd == null ? 'Not recorded for this older transaction' : vnd(t.balance_after_vnd)}</dd></div>
    </dl>
  </div>;
}

function DetailBody({ user, id, ask }: { user: DemoUser; id: string; ask?: (text: string) => void }) {
  const [data, setData] = useState<Transaction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setError(null);
    api.transaction(user, id).then(result => { if (active) setData(result); })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [user, id, attempt]);
  if (error) return <div role="alert" className="form-error">{error}<button className="link-button" onClick={() => setAttempt(n => n + 1)}>Try again</button></div>;
  if (!data) return <p role="status" className="muted">Loading transaction…</p>;
  return <div className="detail-actions">
    <TransactionInfo transaction={data} />
    {user.role === 'customer' && data.direction === 'out' && <CategoryEditor user={user} id={data.id} />}
    {data.status === 'COMPLETED' && <ReceiptButton user={user} transactionId={data.id} />}
    {ask && <button className="secondary-button" onClick={() => ask(`Check transaction ${data.id}`)}>
      <MessageCircle size={18} aria-hidden="true" /> Ask Nova about this
    </button>}
  </div>;
}

function CategoryEditor({ user, id }: { user: DemoUser; id: string }) {
  const op = useOperation();
  return <form className="service-form" onSubmit={e => { e.preventDefault(); const category = new FormData(e.currentTarget).get('category'); void op.run(async () => { await send(user, `/transactions/${encodeURIComponent(id)}/category?category=${category}`, undefined, 'PATCH'); op.setMessage('Category updated for spending analytics.'); }); }}><Field label="Spending category"><select name="category">{['other','food','transport','shopping','electricity','water','internet','mobile','transfer'].map(c => <option key={c}>{c}</option>)}</select></Field><button className="secondary-button" disabled={op.busy}>Save category</button><Feedback state={op} /></form>;
}

export function TransactionDetails({ user, id, onClose, ask }: {
  user: DemoUser; id: string | null; onClose: () => void; ask?: (text: string) => void;
}) {
  return <Sheet open={id !== null} onClose={onClose} title="Transaction details">
    {id && <DetailBody key={id} user={user} id={id} ask={ask} />}
  </Sheet>;
}
