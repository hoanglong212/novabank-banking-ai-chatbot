import { useEffect, useRef, useState, type ReactNode } from 'react';
import { api, request } from '../../api';
import type { DemoUser, Transfer } from '../../types';
import { FactorForm } from '../profile/AuthenticatorSettings';

interface StepUpState {
  required: boolean; new_recipient: boolean; totp_enabled: boolean; enrollment_required: boolean;
  verified: boolean; expires_in: number; confirmation_method: 'email' | null; message: string;
}
const message = (error: unknown) => {
  const text = (error as Error).message;
  return ({ RECIPIENT_COOLING_OFF: 'The recipient waiting period has not ended. Wait, then request the transfer code again.',
    STEP_UP_REQUIRED: 'Verify this transfer with a fresh authenticator code first.',
    AUTHENTICATOR_ENROLLMENT_REQUIRED: 'Set up your authenticator before paying this new recipient.' } as Record<string, string>)[text] ?? text;
};

export function TransferStepUpGate({ user, transfer, step, onTransfer, children }: {
  user: DemoUser; transfer: Transfer; step?: string; onTransfer: (result: Transfer) => void;
  children: (state: { emailConfirmation: boolean }) => ReactNode;
}) {
  const [state, setState] = useState<StepUpState | null>(null);
  const [error, setError] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [enrolled, setEnrolled] = useState(false);
  const mounted = useRef(true);
  const endpoint = '/transfers/' + encodeURIComponent(transfer.id) + '/step-up';
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    let active = true;
    setState(null); setError('');
    request<StepUpState>(endpoint, user).then(result => { if (active) setState(result); })
      .catch(err => { if (active) setError(message(err)); });
    return () => { active = false; };
  }, [endpoint, user, revision]);
  useEffect(() => {
    if (!state?.verified) return;
    const timer = window.setTimeout(() => setRevision(n => n + 1), state.expires_in * 1000);
    return () => clearTimeout(timer);
  }, [state]);

  async function verify() {
    if (busy || code.length !== 6) return;
    setBusy(true); setError('');
    try {
      const result = await request<StepUpState>(endpoint, user, { method: 'POST', body: JSON.stringify({ code }) });
      if (mounted.current) { setState(result); setCode(''); }
    } catch (err) { if (mounted.current) { setError(message(err)); setCode(''); } }
    finally { if (mounted.current) setBusy(false); }
  }
  async function requestCode() {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const result = await api.resendOtp(user, transfer.id);
      if (mounted.current) onTransfer(result);
    } catch (err) { if (mounted.current) setError(message(err)); }
    finally { if (mounted.current) setBusy(false); }
  }
  const origin = (transfer as Transfer & { source_origin?: string }).source_origin;
  const provenance = origin === 'qr' || origin === 'ocr'
    ? <p className="muted small">These payment details came from {origin === 'qr' ? 'a QR code' : 'an uploaded image'}. Check the recipient and amount independently.</p> : null;
  const warning = state?.required && <p className="form-error" role="note">New recipient. Authenticator verification is required before the bank sends a transfer code.</p>;
  if (step === 'review') return <>{provenance}{warning}{children({ emailConfirmation: false })}</>;
  if (!state) return <>{provenance}{error
    ? <div role="alert" className="form-error">{error} <button type="button" className="link-button" onClick={() => setRevision(n => n + 1)}>Try recipient verification again</button></div>
    : <p role="status" className="muted">Checking recipient verification…</p>}</>;
  if (!state.required) return <>{provenance}{children({ emailConfirmation: false })}</>;
  if (state.enrollment_required) return <section aria-label="Set up verification for this recipient">
    {provenance}{warning}<h3>Set up your authenticator</h3>
    <p className="muted">A transaction PIN cannot replace authenticator verification for a new recipient. No money has moved.</p>
    <FactorForm user={user} action="setup" done={() => { setEnrolled(true); setRevision(n => n + 1); }} />
  </section>;
  if (!state.verified) return <section aria-label="Verify new recipient">
    {provenance}{warning}<h3>Verify this new recipient</h3>
    <p className="muted">Enter a fresh code from your authenticator for this exact transfer. {enrolled ? 'Setup used the previous code. ' : ''}If you just signed in or used a code, wait for the next one. The code must be entered here, never in chat.</p>
    {error && <p role="alert" className="form-error">{error}</p>}
    <form className="qr-form" onSubmit={event => { event.preventDefault(); void verify(); }}>
      <label className="field"><span>New-recipient authenticator code</span><input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required value={code} disabled={busy} onChange={event => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} /></label>
      <button className="primary-button" disabled={busy || code.length !== 6}>{busy ? 'Verifying…' : 'Verify new recipient'}</button>
    </form>
  </section>;
  if (transfer.otp_method !== 'email') return <section aria-label="Request transfer confirmation code">
    {provenance}<p role="status">Authenticator verification passed for this transfer. No money has moved.</p>
    {error && <p role="alert" className="form-error">{error}</p>}
    <button type="button" className="primary-button" disabled={busy} onClick={() => void requestCode()}>{busy ? 'Requesting code…' : 'Request transfer verification code'}</button>
  </section>;
  return <>{provenance}{children({ emailConfirmation: true })}</>;
}
