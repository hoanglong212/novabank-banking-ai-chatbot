import { useEffect, useRef, useState, type FormEvent } from 'react';
import { CheckCircle2, MessageSquareText } from 'lucide-react';

import { api } from '../../api';
import type { Bank, DemoUser, Transfer, TransferStart } from '../../types';
import { vnd } from '../../format';
import { BankPicker } from '../qr/BankPicker';
import { Sheet } from '../ui/Sheet';

const NOVABANK: Bank = { bin: 'NovaBank', code: 'NOVA', shortName: 'NovaBank', name: 'Internal transfer · instant, free', logo: '' };
const AMOUNTS = [50000, 100000, 200000, 500000];
const ERRORS: Record<string, string> = {
  INSUFFICIENT_FUNDS: 'Your balance is lower than this amount.',
  RECIPIENT_NOT_FOUND: 'No NovaBank account has this ID.',
  SAME_ACCOUNT: 'You cannot transfer to the same account.',
  UNKNOWN_BANK: 'This bank is not supported.',
  INVALID_ACCOUNT: 'Other banks use numeric account numbers.',
  ACCOUNT_NOT_OWNED: 'You can only pay from your own account.',
  OTP_INVALID: 'Wrong OTP. Check the SMS and try again.',
  OTP_EXPIRED: 'The OTP has expired. Tap “Resend OTP”.',
  OTP_LOCKED: 'Too many wrong OTPs. This transfer was cancelled.',
  ALREADY_PROCESSED: 'This transfer was already completed or cancelled.',
  DAILY_LIMIT_EXCEEDED: 'This transfer exceeds your daily limit.',
  TRANSFER_NOT_FOUND: 'Transfer not found.',
  VIETQR_UNAVAILABLE: 'The bank list is unavailable. Try again shortly.',
};
const explain = (err: unknown) => ERRORS[(err as Error).message] ?? (err as Error).message;

interface TransferSheetProps {
  user: DemoUser;
  start: TransferStart | null;
  onClose: () => void;
  onDone: () => void;
}

// Sheet renders its children only while open, so every opening starts a fresh flow.
export function TransferSheet({ user, start, onClose, onDone }: TransferSheetProps) {
  return (
    <Sheet open={start !== null} onClose={onClose} title="Transfer money">
      {start && <TransferFlow user={user} start={start} onClose={onClose} onDone={onDone} />}
    </Sheet>
  );
}

// form -> review + OTP (simulated SMS) -> receipt, as in Vietnamese banking apps.
function TransferFlow({ user, start, onClose, onDone }: TransferSheetProps & { start: TransferStart }) {
  const [banks, setBanks] = useState<Bank[]>([NOVABANK]);
  const [bank, setBank] = useState(start.to_bank ?? 'NovaBank');
  const [account, setAccount] = useState(start.to_account ?? '');
  const [name, setName] = useState(start.to_name ?? '');
  const [amount, setAmount] = useState(start.amount_vnd ? String(start.amount_vnd) : '');
  const [content, setContent] = useState(start.content ?? '');
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [otp, setOtp] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const internal = bank === 'NovaBank';
  const validAccount = internal ? /^ACC-[A-Z0-9-]{3,30}$/.test(account) : /^\d{6,19}$/.test(account);

  const otpRequested = useRef(false);

  useEffect(() => {
    api.banks(user).then(list => setBanks([NOVABANK, ...list])).catch(() => { /* NovaBank transfers still work */ });
    // A draft prepared by Nova: fetch it with a fresh OTP and go straight to review.
    // Once only: StrictMode's second run would issue a second OTP and race the first.
    if (start.draftId && !otpRequested.current) {
      otpRequested.current = true;
      api.resendOtp(user, start.draftId).then(setTransfer).catch(err => setError(explain(err)));
    }
  }, [user, start.draftId]);

  async function run(action: () => Promise<Transfer>) {
    setBusy(true);
    setError(null);
    try {
      const result = await action();
      setTransfer(result);
      if (result.status === 'COMPLETED') onDone();
    } catch (err) {
      setError(explain(err));
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(() => api.createTransfer(user, {
      to_bank: bank, to_account: account, amount_vnd: Number(amount),
      content: content || undefined, to_name: internal ? undefined : name || undefined,
    }));
  }

  function confirm(event: FormEvent) {
    event.preventDefault();
    void run(() => api.confirmTransfer(user, transfer!.id, otp));
  }

  if (transfer?.status === 'COMPLETED') {
    return (
      <div className="tx-detail">
        <span className="tx-icon tx-icon-lg in"><CheckCircle2 size={30} aria-hidden="true" /></span>
        <strong>Transfer successful</strong>
        <strong className="tx-detail-amount">-{vnd(transfer.amount_vnd)}</strong>
        <dl className="detail-list">
          <div><dt>To</dt><dd>{transfer.to_name || 'Name not verified'}</dd></div>
          <div><dt>Bank</dt><dd>{transfer.to_bank} · {transfer.to_account}</dd></div>
          <div><dt>Content</dt><dd>{transfer.content}</dd></div>
          <div><dt>Reference</dt><dd>{transfer.transaction_id}</dd></div>
          {transfer.balance_vnd !== undefined && <div><dt>New balance</dt><dd>{vnd(transfer.balance_vnd)}</dd></div>}
        </dl>
        <button className="primary-button" onClick={onClose}>Done</button>
      </div>
    );
  }

  if (transfer) {
    return (
      <form className="qr-form" onSubmit={confirm} noValidate>
        <dl className="detail-list">
          <div><dt>From</dt><dd>{transfer.from_account}</dd></div>
          <div><dt>To</dt><dd>{transfer.to_name || 'Name not verified (other bank)'}</dd></div>
          <div><dt>Bank</dt><dd>{transfer.to_bank} · {transfer.to_account}</dd></div>
          <div><dt>Amount</dt><dd>{vnd(transfer.amount_vnd)}</dd></div>
          <div><dt>Fee</dt><dd>Free</dd></div>
          <div><dt>Content</dt><dd>{transfer.content}</dd></div>
        </dl>
        {transfer.demo_otp && (
          <div className="sms-box" role="status">
            <MessageSquareText size={18} aria-hidden="true" />
            <span><strong>Simulated SMS from NovaBank</strong><br />OTP for {transfer.id}: <b>{transfer.demo_otp}</b>. Valid 2 minutes. Never share it, not even with Nova.</span>
          </div>
        )}
        {error && <div className="form-error" role="alert">{error}</div>}
        <label className="field">
          <span>Enter OTP</span>
          <input className="otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={otp} placeholder="••••••"
            onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} />
        </label>
        <button className="primary-button" type="submit" disabled={busy || otp.length !== 6}>{busy ? 'Confirming…' : 'Confirm transfer'}</button>
        <button className="link-button" type="button" disabled={busy} onClick={() => run(() => api.resendOtp(user, transfer.id))}>Resend OTP</button>
      </form>
    );
  }

  if (start.draftId) return error ? <div className="form-error" role="alert">{error}</div> : <p className="muted">Loading transfer…</p>;

  return (
    <form className="qr-form" onSubmit={submit} noValidate>
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="field">
        <span>Recipient bank</span>
        <BankPicker banks={banks} value={bank} onChange={b => { setBank(b); setAccount(''); }} />
      </div>
      <label className="field">
        <span>{internal ? 'NovaBank account ID' : 'Account number'}</span>
        <input autoComplete="off" value={account} placeholder={internal ? 'ACC-BOB-001' : '6–19 digits'}
          inputMode={internal ? 'text' : 'numeric'} aria-invalid={account !== '' && !validAccount}
          onChange={e => setAccount(internal ? e.target.value.toUpperCase().trim() : e.target.value.replace(/\D/g, '').slice(0, 19))} />
      </label>
      {!internal && (
        <label className="field">
          <span>Recipient name <small>optional</small></span>
          <input value={name} maxLength={50} placeholder="NGUYEN VAN A" onChange={e => setName(e.target.value.toUpperCase())} />
        </label>
      )}
      <label className="field">
        <span>Amount</span>
        <span className="input-suffix">
          <input inputMode="numeric" value={amount ? Number(amount).toLocaleString('en-US') : ''} placeholder="0"
            onChange={e => setAmount(e.target.value.replace(/\D/g, '').slice(0, 9))} />
          <span aria-hidden="true">VND</span>
        </span>
      </label>
      <div className="amount-chips" aria-label="Quick amounts">
        {AMOUNTS.map(a => <button type="button" key={a} className={Number(amount) === a ? 'is-active' : ''}
          onClick={() => setAmount(String(a))}>{a.toLocaleString('en-US')}</button>)}
      </div>
      <label className="field">
        <span>Content <small>optional</small></span>
        <input value={content} maxLength={25} placeholder={`${user.name} transfer`} onChange={e => setContent(e.target.value)} />
      </label>
      <button className="primary-button" type="submit" disabled={busy || !validAccount || Number(amount) < 1000}>
        {busy ? 'Checking…' : 'Continue'}
      </button>
    </form>
  );
}
