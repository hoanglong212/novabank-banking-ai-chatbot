import { useState, type FormEvent } from 'react';
import { KeyRound } from 'lucide-react';
import { api } from '../../api';
import type { DemoUser, MfaStatus } from '../../types';
import { Sheet } from '../ui/Sheet';

const weak = (pin: string) => new Set(pin).size === 1 || '0123456789'.includes(pin) || '9876543210'.includes(pin);
const digits = (value: string) => value.replace(/\D/g, '').slice(0, 6);

/** Set or change the 6-digit transaction PIN. The current password proves it is the account owner. */
export function PinForm({ user, done, submitLabel = 'Save PIN' }: { user: DemoUser; done: (message: string) => void; submitLabel?: string }) {
  const [password, setPassword] = useState('');
  const [pin, setPin] = useState('');
  const [again, setAgain] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mismatch = again.length === 6 && again !== pin;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (weak(pin)) { setError('Choose a PIN that is not repeated or sequential digits, like 111111 or 123456.'); return; }
    setBusy(true); setError(null);
    try { done((await api.setPin(user, password, pin)).message); }
    catch (err) { setError((err as Error).message); setPassword(''); }
    finally { setBusy(false); }
  }
  return <form className="security-form pin-form" onSubmit={submit} aria-busy={busy}>
    {error && <p className="form-error" role="alert">{error}</p>}
    <label className="field"><span>Current password</span>
      <input type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={e => setPassword(e.target.value)} disabled={busy} />
    </label>
    <div className="pin-pair">
      <label className="field"><span>New 6-digit PIN</span>
        <input className="pin-input" type="password" inputMode="numeric" autoComplete="new-password" required pattern="[0-9]{6}" maxLength={6}
          value={pin} onChange={e => setPin(digits(e.target.value))} disabled={busy} />
      </label>
      <label className="field"><span>Repeat PIN</span>
        <input className="pin-input" type="password" inputMode="numeric" autoComplete="new-password" required pattern="[0-9]{6}" maxLength={6}
          value={again} onChange={e => setAgain(digits(e.target.value))} disabled={busy} aria-invalid={mismatch} aria-describedby="pin-hint" />
      </label>
    </div>
    <p id="pin-hint" className={`small ${mismatch ? 'form-error-text' : 'muted'}`}>{mismatch ? 'The two PINs do not match.' : 'Avoid birthdays and patterns like 111111 or 123456. Never share it, not even with Nova.'}</p>
    <button className="primary-button" disabled={busy || !password || pin.length !== 6 || again !== pin}>{busy ? 'Saving…' : submitLabel}</button>
  </form>;
}

export function TransactionPinSettings({ user, status, changed }: { user: DemoUser; status: MfaStatus; changed: (message: string) => void }) {
  const [open, setOpen] = useState(false);
  return <>
    <p><strong>{status.pin_set ? 'Transaction PIN set' : 'No transaction PIN yet'}</strong></p>
    <p className="muted small">{status.pin_set
      ? 'Use your PIN for transfers to verified recipients. The bank also checks your authenticator when you pay a new recipient.'
      : 'Set a 6-digit PIN to confirm future transfers to verified recipients.'}</p>
    <button className="secondary-button" onClick={() => setOpen(true)}><KeyRound size={16} aria-hidden="true" /> {status.pin_set ? 'Change PIN' : 'Create PIN'}</button>
    <Sheet open={open} onClose={() => setOpen(false)} title={status.pin_set ? 'Change transaction PIN' : 'Create transaction PIN'}>
      {open && <PinForm user={user} done={message => { setOpen(false); changed(message); }} />}
    </Sheet>
  </>;
}
