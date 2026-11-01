import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '../../api';
import type { LoginResponse, MfaChallenge } from '../../types';
import { AuthShell } from './AuthShell';

export function MfaSignIn({ challenge, complete, cancel }: {
  challenge: MfaChallenge; complete: (session: LoginResponse) => void; cancel: () => void;
}) {
  const [method, setMethod] = useState(challenge.method);
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState(challenge.message);
  const [busy, setBusy] = useState(false);
  const [expiresAt] = useState(() => Date.now() + challenge.expires_in * 1000);
  const [resendAt, setResendAt] = useState(() => Date.now() + (method === 'email' ? 30_000 : 0));
  const [now, setNow] = useState(Date.now);
  const request = useRef(0);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => { clearInterval(timer); request.current++; };
  }, []);
  const expired = now >= expiresAt;
  const cooldown = Math.max(0, Math.ceil((resendAt - now) / 1000));

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (busy || expired) return;
    const id = ++request.current;
    setBusy(true); setError(null);
    try {
      const result = await api.verifyMfa(challenge.challenge_id, code);
      if (id === request.current) complete(result);
    } catch (err) { if (id === request.current) setError((err as Error).message); }
    finally { if (id === request.current) { setBusy(false); setCode(''); } }
  }

  async function email() {
    if (busy || expired || cooldown) return;
    const id = ++request.current;
    setBusy(true); setError(null);
    try {
      const result = await api.resendMfa(challenge.challenge_id);
      if (id !== request.current) return;
      setMethod('email'); setMessage(result.message); setCode(''); setResendAt(Date.now() + 30_000);
    } catch (err) { if (id === request.current) setError((err as Error).message); }
    finally { if (id === request.current) setBusy(false); }
  }

  return <AuthShell><form className="login-card" onSubmit={verify} aria-busy={busy}>
    <span className="brand-mark login-mark" aria-hidden="true">N</span>
    <h1 ref={heading} tabIndex={-1}>Verify sign-in</h1>
    <p className="login-sub">{method === 'totp' ? 'Enter the code from your authenticator app.' : 'Enter the six-digit code from your local demo inbox.'}</p>
    {expired ? <p className="form-error" role="alert">This sign-in request expired. Return to sign in.</p>
      : error ? <p className="form-error" role="alert">{error}</p> : <p className="auth-hint" role="status">{message}</p>}
    <label className="field"><span>Verification code</span>
      <input autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6}
        required value={code} onChange={event => setCode(event.target.value.replace(/\D/g, ''))} disabled={busy || expired} />
    </label>
    <button className="primary-button" disabled={busy || expired || code.length !== 6}>
      {busy ? 'Please wait…' : 'Verify and sign in'}
    </button>
    <div className="auth-links">
      <button type="button" onClick={() => void email()} disabled={busy || expired || cooldown > 0}>
        {method === 'totp' ? 'Use an email code instead' : cooldown ? `Resend code in ${cooldown}s` : 'Resend code'}
      </button>
      <button type="button" disabled={busy} onClick={cancel}>Back to sign in</button>
    </div>
    <p className="auth-hint">No real email is sent. Open the local inbox with the command in the demo instructions. Codes stay outside the assistant.</p>
  </form></AuthShell>;
}
