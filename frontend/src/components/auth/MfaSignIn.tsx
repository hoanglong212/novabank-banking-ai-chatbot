import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '../../api';
import type { LoginResponse, MfaChallenge } from '../../types';
import { ShieldCheck, Mail } from 'lucide-react';
import { AuthBack, AuthHeading, AuthSubmit } from './AuthUi';
import { VerificationCode } from './VerificationCode';

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

  return <form className="auth-form auth-form-mfa" onSubmit={verify} aria-busy={busy}>
    <AuthBack onClick={cancel} disabled={busy} />
    <AuthHeading headingRef={heading} icon={ShieldCheck} eyebrow="A LITTLE EXTRA PEACE OF MIND" title="Verify sign-in"
      subtitle={method === 'totp' ? 'Enter the code from your authenticator app.' : 'Enter the six-digit code from your local demo inbox.'} />
    {expired ? <p className="form-error" role="alert">This sign-in request expired. Return to sign in.</p>
      : error ? <p className="form-error" role="alert">{error}</p> : <p className="auth-code-status" role="status">{message}</p>}
    <VerificationCode value={code} onChange={setCode} disabled={busy || expired} invalid={!!error || expired} shake={!!error && !expired} />
    <p className="auth-code-help" id="auth-code-help">{expired ? 'Request a new sign-in to continue.' : 'You can paste all six digits at once.'}</p>
    <AuthSubmit busy={busy} disabled={expired || code.length !== 6}>Verify and sign in</AuthSubmit>
    <div className="auth-secondary-actions">
      <button type="button" onClick={() => void email()} disabled={busy || expired || cooldown > 0}>
        {method === 'totp' ? 'Use an email code instead' : cooldown ? `Resend code in ${cooldown}s` : 'Resend code'}
      </button>
    </div>
    <p className="auth-local-note"><Mail size={15} aria-hidden="true" /><span>No real email is sent. Find your code in the local demo inbox. Codes stay outside the assistant.</span></p>
  </form>;
}
