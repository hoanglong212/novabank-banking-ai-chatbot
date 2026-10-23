import { useEffect, useState } from 'react';
import { api } from '../api';
import type { BankAccount, BankTransaction, DemoUser, TransferIntent } from '../types';
import '../styles/banking.css';

const money = (value: number) => value.toLocaleString('en-US') + ' VND';

export function BankingPanel({ user }: { user: DemoUser }) {
  const [accounts,setAccounts] = useState<BankAccount[]>([]);
  const [history,setHistory] = useState<BankTransaction[]>([]);
  const [source,setSource] = useState('');
  const [recipient,setRecipient] = useState('');
  const [amount,setAmount] = useState('');
  const [description,setDescription] = useState('');
  const [intent,setIntent] = useState<TransferIntent | null>(null);
  const [receipt,setReceipt] = useState<BankTransaction | null>(null);
  const [busy,setBusy] = useState(true);
  const [error,setError] = useState('');
  const storageKey = 'novabank-transfer-preview-'+user.id;
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [rows,transactions] = await Promise.all([api.accounts(),api.transactions()]);
        if (!active) return;
        setAccounts(rows); setSource(rows[0]?.id || ''); setHistory(transactions);
        const saved = window.sessionStorage.getItem(storageKey);
        if (saved) {
          const draft = await api.transferIntent(saved);
          if (!active) return;
          if (draft.status === 'pending') setIntent(draft);
          else {
            window.sessionStorage.removeItem(storageKey);
            if (draft.status === 'completed') setReceipt(transactions.find(t => t.intent_id === saved) || null);
          }
        }
      } catch (e) { if (active) setError((e as Error).message); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  },[storageKey]);

  async function refresh() {
    const [rows,transactions] = await Promise.all([api.accounts(),api.transactions()]);
    setAccounts(rows); setHistory(transactions);
  }
  async function confirm() {
    if (!intent || busy) return;
    setBusy(true); setError('');
    try {
      const result = await api.confirmTransfer(intent.id);
      setReceipt(result); setIntent(null);
      window.sessionStorage.removeItem(storageKey);
      await refresh();
    } catch (e) {
      setError((e as Error).message + ' Review the status before retrying; the same preview will be reused.');
    } finally { setBusy(false); }
  }
  async function edit() {
    if (!intent || busy) return;
    setBusy(true); setError('');
    try {
      await api.cancelTransfer(intent.id);
      setSource(intent.source_account_id); setRecipient(intent.recipient_account_id);
      setAmount(String(intent.amount_vnd)); setDescription(intent.description);
      setIntent(null); window.sessionStorage.removeItem(storageKey);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <section className="banking-panel" aria-label="Accounts and transfers">
    <h1>Accounts & transfers</h1>
    <p>Simulated money. Transfers are available between NovaBank demo accounts.</p>
    <div className="account-cards">{accounts.map(account => <article key={account.id} className="bank-card">
      <span>{account.owner_name} · {account.id}</span><strong>{money(account.balance_vnd)}</strong>
    </article>)}</div>
    {error && <p role="alert" className="bank-error">{error}</p>}
    {busy && <p role="status">Updating…</p>}
    {receipt && <article className="bank-card" aria-label="Transfer receipt">
      <h2>Transfer completed</h2><strong>{money(receipt.amount_vnd)}</strong>
      <p>To {receipt.recipient_account_id}</p><p>Reference: {receipt.id}</p>
      <p>{receipt.created_at} · {receipt.status}</p>
      <button onClick={() => setReceipt(null)} disabled={busy}>New transfer</button>
    </article>}
    {!receipt && (intent ? <article className="bank-card" aria-label="Transfer preview">
      <h2>Review transfer</h2><p>From {intent.source_account_id}</p>
      <p>To {intent.recipient_name} · {intent.recipient_account_id}</p>
      <strong>{money(intent.amount_vnd)}</strong><p>{intent.description}</p>
      <p>Preview expires at {new Date(intent.expires_at*1000).toLocaleTimeString()}.</p>
      <div className="bank-actions"><button onClick={confirm} disabled={busy}>Confirm transfer</button>
      <button onClick={edit} disabled={busy}>Edit details</button></div>
    </article> : <form className="bank-card" onSubmit={async event => {
      event.preventDefault();
      if (busy) return;
      if (!/^\d+$/.test(amount) || !Number.isSafeInteger(Number(amount)) || Number(amount)<=0 || Number(amount)>1e12) {
        setError('Enter a positive whole amount in VND (maximum 1,000,000,000,000).'); return;
      }
      setBusy(true); setError('');
      try {
        const next = await api.previewTransfer({source_account_id:source,recipient_account_id:recipient.trim(),amount_vnd:Number(amount),description});
        setIntent(next); window.sessionStorage.setItem(storageKey,next.id);
      } catch (e) { setError((e as Error).message); }
      finally { setBusy(false); }
    }}>
      <h2>New transfer</h2>
      <label>From account<select value={source} onChange={e => setSource(e.target.value)} required disabled={busy}>
        {accounts.map(a => <option key={a.id}>{a.id}</option>)}
      </select></label>
      <label>Recipient account<input name="recipient" value={recipient} onChange={e => setRecipient(e.target.value)} placeholder="ACC-BOB-001" maxLength={40} required disabled={busy} /></label>
      <label>Amount (VND)<input name="amount" inputMode="numeric" value={amount} onChange={e => setAmount(e.target.value)} required disabled={busy} /></label>
      <label>Description<input name="description" value={description} onChange={e => setDescription(e.target.value)} maxLength={140} disabled={busy} /></label>
      <button type="submit" disabled={busy || !accounts.length}>Review transfer</button>
    </form>)}
    <div className="bank-history"><h2>Recent transactions</h2>
      <button type="button" disabled={busy} onClick={async () => {
        setBusy(true); setError('');
        try { await refresh(); } catch(e) { setError((e as Error).message); } finally { setBusy(false); }
      }}>Refresh history</button>
      {history.map(transaction => <article key={transaction.id} className="bank-card">
        <strong>{money(transaction.amount_vnd)} · {transaction.status}</strong>
        <p>{transaction.id}</p><p>From {transaction.source_account_id}{transaction.recipient_account_id ? ' → '+transaction.recipient_account_id : ''}</p>
        <p>{transaction.description}</p><small>{transaction.created_at}</small>
      </article>)}
    </div>
  </section>;
}
