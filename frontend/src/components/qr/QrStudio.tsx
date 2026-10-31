import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Download, QrCode, ScanLine } from 'lucide-react';

import { api } from '../../api';
import type { Bank, DemoUser, TransferStart, VietQR } from '../../types';
import { vnd } from '../../format';
import { BankPicker } from './BankPicker';

const AMOUNTS = [50000, 100000, 200000, 500000];

export function QrStudio({ user, pay }: { user: DemoUser; pay: (start: TransferStart) => void }) {
  const [banks, setBanks] = useState<Bank[]>([]);
  const [bank, setBank] = useState('970436');
  const [accountNo, setAccountNo] = useState('');
  const [accountName, setAccountName] = useState('');
  const [amount, setAmount] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qr, setQr] = useState<VietQR | null>(null);
  const resultRef = useRef<HTMLElement>(null);

  useEffect(() => {
    api.banks(user).then(setBanks).catch(err => setError(err.message));
  }, [user]);

  const validAccount = /^\d{6,19}$/.test(accountNo);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setQr(await api.createVietQR(user, {
        bank, account_no: accountNo, account_name: accountName || undefined,
        amount_vnd: amount ? Number(amount) : undefined, add_info: info || undefined,
      }));
      // On phones the result sits below the form.
      window.setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
    } catch (err) {
      setError((err as Error).message === 'UNKNOWN_BANK' ? 'This bank is not supported by VietQR.' : (err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">VietQR</h1>
      <div className="qr-layout">
        <form className="card qr-form" onSubmit={submit} noValidate>
          <h2 className="card-title">Create a payment code</h2>
          {error && <div className="form-error" role="alert">{error}</div>}
          <div className="field">
            <span>Bank</span>
            <BankPicker banks={banks} value={bank} onChange={setBank} />
          </div>
          <label className="field">
            <span>Account number</span>
            <input inputMode="numeric" autoComplete="off" value={accountNo} placeholder="6–19 digits"
              onChange={e => setAccountNo(e.target.value.replace(/\D/g, '').slice(0, 19))}
              aria-invalid={accountNo !== '' && !validAccount} />
          </label>
          <label className="field">
            <span>Account name <small>optional</small></span>
            <input value={accountName} maxLength={50} placeholder="NGUYEN VAN A" onChange={e => setAccountName(e.target.value.toUpperCase())} />
          </label>
          <label className="field">
            <span>Amount <small>optional</small></span>
            <span className="input-suffix">
              <input inputMode="numeric" value={amount ? Number(amount).toLocaleString('en-US') : ''} placeholder="0"
                onChange={e => setAmount(e.target.value.replace(/\D/g, '').slice(0, 11))} />
              <span aria-hidden="true">VND</span>
            </span>
          </label>
          <div className="amount-chips" aria-label="Quick amounts">
            {AMOUNTS.map(a => <button type="button" key={a} className={Number(amount) === a ? 'is-active' : ''}
              onClick={() => setAmount(String(a))}>{a.toLocaleString('en-US')}</button>)}
          </div>
          <label className="field">
            <span>Transfer content <small>optional · max 25 characters</small></span>
            <input value={info} maxLength={25} placeholder="e.g. coffee" onChange={e => setInfo(e.target.value)} />
          </label>
          <button className="primary-button" type="submit" disabled={busy || !validAccount}>
            {busy ? 'Creating…' : 'Create QR code'}
          </button>
        </form>

        <section ref={resultRef} className={`card qr-result ${qr ? 'has-qr' : ''}`} aria-live="polite">
          {qr ? (
            <>
              <img key={qr.image} src={qr.image} alt={`VietQR code for ${qr.bank} account ending ${qr.account_no.slice(-4)}`} />
              <dl className="detail-list">
                <div><dt>Bank</dt><dd>{qr.bank}</dd></div>
                <div><dt>Account</dt><dd>•••• {qr.account_no.slice(-4)}</dd></div>
                {qr.account_name && <div><dt>Name</dt><dd>{qr.account_name}</dd></div>}
                {qr.amount_vnd && <div><dt>Amount</dt><dd>{vnd(qr.amount_vnd)}</dd></div>}
                {qr.add_info && <div><dt>Content</dt><dd>{qr.add_info}</dd></div>}
              </dl>
              {/* Simulates another customer scanning this code: the transfer form opens prefilled from the QR. */}
              <button className="primary-button" onClick={() => pay({
                to_bank: qr.bin, to_account: qr.account_no, to_name: qr.account_name || undefined,
                amount_vnd: qr.amount_vnd ?? undefined, content: qr.add_info || undefined,
              })}><ScanLine size={18} aria-hidden="true" /> Scan &amp; pay (simulated)</button>
              <a className="secondary-button" href={qr.image} target="_blank" rel="noopener noreferrer"><Download size={18} aria-hidden="true" /> Open image</a>
              <p className="muted small">Anyone scanning this code pays the account above. Always confirm the recipient name in the banking app.</p>
            </>
          ) : (
            <div className="qr-empty">
              <QrCode size={56} aria-hidden="true" />
              <strong>Your QR code appears here</strong>
              <span className="muted small">Works with every Vietnamese banking app via NAPAS 247.</span>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
