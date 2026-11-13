import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '../../api';
import type { DemoUser, MfaStatus } from '../../types';
import { Sheet } from '../ui/Sheet';
import { openInbox } from '../dev/Outbox';

type Action = 'setup' | 'disable';
export function AuthenticatorSettings({ user, status, changed }: {
  user: DemoUser; status: MfaStatus; changed: (message: string) => void;
}) {
  const [action, setAction] = useState<Action | null>(null);
  return <>
    <p><strong>{status.totp_enabled ? 'Authenticator enabled' : 'Email codes enabled'}</strong></p>
    <p className="muted small">{status.totp_enabled
      ? 'Sign-ins, transfers and payments use a code from your authenticator app. Email codes remain available for sign-in if you cannot use the app.'
      : 'Every sign-in needs a code from the local demo inbox. Add an authenticator app for another way to verify.'}</p>
    <button className="secondary-button" onClick={() => setAction(status.totp_enabled ? 'disable' : 'setup')}>
      {status.totp_enabled ? 'Disable authenticator' : 'Set up authenticator'}
    </button>
    <Sheet open={action !== null} onClose={() => setAction(null)} title={action === 'disable' ? 'Disable authenticator' : 'Set up authenticator'}>
      {action && <FactorForm user={user} action={action} done={message => { setAction(null); changed(message); }} />}
    </Sheet>
  </>;
}

export function FactorForm({ user, action, done }: { user: DemoUser; action: Action; done: (message: string) => void }) {
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [pending, setPending] = useState<{ secret?: string; qr?: string; challengeId?: string; expiresAt: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef(0);
  useEffect(() => () => { request.current++; }, []);
  useEffect(() => {
    if (!pending) return;
    const timer = window.setTimeout(() => { request.current++; setPending(null); setPassword(''); setCode(''); setBusy(false);
      setError('This request expired. Enter your password to start again.'); }, Math.max(0, pending.expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [pending]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const id = ++request.current;
    setBusy(true); setError(null);
    try {
      if (!pending) {
        if (action === 'setup') {
          const result = await api.setupTotp(user, password);
          if (id === request.current) setPending({ secret: result.secret, qr: result.qr_png, expiresAt: Date.now() + result.expires_in * 1000 });
        } else {
          const result = await api.disableTotpRequest(user, password);
          if (id === request.current) setPending({ challengeId: result.challenge_id, expiresAt: Date.now() + result.expires_in * 1000 });
        }
      } else {
        const result = action === 'setup' ? await api.enableTotp(user, code) : await api.disableTotp(user, pending.challengeId!, code);
        if (id === request.current) done(result.message);
      }
    } catch (err) { if (id === request.current) setError((err as Error).message); }
    finally { if (id === request.current) { setBusy(false); setPassword(''); setCode(''); } }
  }

  return <form className="security-form" onSubmit={submit} aria-busy={busy}>
    <p className="muted">{action === 'setup'
      ? 'Add NovaBank to your authenticator app, then enter a code to confirm setup. Other sessions will be signed out.'
      : 'Confirm with your password and an email code. Email verification will remain required, and other sessions will be signed out.'}</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!pending ? <label className="field"><span>Current password</span>
      <input type="password" autoComplete="current-password" required maxLength={128} value={password}
        onChange={event => setPassword(event.target.value)} disabled={busy} />
    </label> : <>
      {pending.secret ? <>
        {pending.qr && <figure className="totp-qr"><img src={pending.qr} alt="QR code to add NovaBank to your authenticator app" width={180} height={180} />
          <figcaption>Scan with Google Authenticator, Microsoft Authenticator or similar.</figcaption></figure>}
        <p className="small">{pending.qr ? 'Or add a time-based account named NovaBank with this key.' : 'In your app, add a time-based account named NovaBank and enter this key.'} Keep the key private.</p>
        <label className="field"><span>Setup key</span><input className="setup-key" readOnly value={pending.secret} autoComplete="off" spellCheck={false} /></label>
      </> : <p className="auth-hint">Open the email confirmation code in your local demo inbox. It is valid for two minutes. <button type="button" className="link-button" onClick={() => openInbox()}>Open demo inbox</button></p>}
      <label className="field"><span>{action === 'setup' ? 'Authenticator code' : 'Email confirmation code'}</span>
        <input inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" minLength={6} maxLength={6}
          value={code} onChange={event => setCode(event.target.value.replace(/\D/g, ''))} disabled={busy} />
      </label>
      {action === 'disable' && <button className="secondary-button" type="button" disabled={busy}
        onClick={() => { setPending(null); setCode(''); setError(null); }}>Request another confirmation code</button>}
    </>}
    <button className="primary-button" disabled={busy || (pending ? code.length !== 6 : !password)}>
      {busy ? 'Please wait…' : pending ? action === 'setup' ? 'Enable authenticator' : 'Confirm disable'
        : action === 'setup' ? 'Continue' : 'Send confirmation code'}
    </button>
  </form>;
}
