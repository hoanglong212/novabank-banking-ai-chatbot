import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { api } from '../../api';
import { AuthShell } from './AuthShell';
import { Login } from './Login';
import type { AuthLink } from './authLink';
import type { LoginResponse, MfaChallenge } from '../../types';
import { MfaSignIn } from './MfaSignIn';

type Mode = 'login' | 'register' | 'resend' | 'forgot' | 'verify' | 'reset';
const titles: Record<Mode, string> = { login: 'Sign in', register: 'Create account', resend: 'Verify your email',
  forgot: 'Forgot password?', verify: 'Verify your email', reset: 'Choose a new password' };
const subtitles: Record<Mode, string> = { login: '', register: 'Start with a free, zero-balance demo account.',
  resend: 'Open the verification link in the local demo inbox.', forgot: 'We’ll help you get back into your demo account.',
  verify: 'Confirm your email to open your demo account.', reset: 'Reset links work once and expire after 15 minutes.' };

export function AuthFlow({ onLogin, onVerified, notice, link }: {
  onLogin: (username: string, password: string) => Promise<MfaChallenge>;
  onVerified: (session: LoginResponse) => void; notice: string | null; link: AuthLink | null;
}) {
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const [mode, setMode] = useState<Mode>(link?.mode || 'login');
  const [token, setToken] = useState(link?.token || '');
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const withPassword = mode === 'register' || mode === 'reset';
  const invalidLink = (mode === 'reset' || mode === 'verify') && !token;

  useEffect(() => { heading.current?.focus(); }, [mode]);

  function navigate(next: Mode) {
    setMode(next); setError(null); setMessage(null); setPassword(''); setConfirmation(''); setReveal(false);
    if (next !== 'reset' && next !== 'verify') setToken('');
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError(null); setMessage(null);
    if (withPassword && password !== confirmation) { setError('Passwords do not match. Please try again.'); return; }
    setBusy(true);
    try {
      let result: { message: string };
      if (mode === 'register') {
        result = await api.register({ username, name, email, password });
        setMode('resend');
      } else if (mode === 'resend') result = await api.resendVerification(email);
      else if (mode === 'forgot') result = await api.forgotPassword(email);
      else if (mode === 'verify') { result = await api.verifyEmail(token); setToken(''); setMode('login'); }
      else if (mode === 'reset') { result = await api.resetPassword(token, password); setToken(''); setMode('login'); }
      else return;
      setPassword(''); setConfirmation(''); setReveal(false); setMessage(result.message);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  if (challenge) return <MfaSignIn challenge={challenge} complete={onVerified} cancel={() => setChallenge(null)} />;
  if (mode === 'login') return <Login onLogin={async (username, password) => {
    const result = await onLogin(username, password);
    if (alive.current) setChallenge(result);
  }} notice={notice} success={message} onNavigate={navigate} />;

  return <AuthShell>
    <form className="login-card" onSubmit={submit} aria-busy={busy}>
      <span className="brand-mark login-mark" aria-hidden="true">N</span>
      <h1 tabIndex={-1} ref={heading}>{titles[mode]}</h1>
      <p className="login-sub">{subtitles[mode]}</p>
      {(error || invalidLink) && <div className="form-error" role="alert">{error || 'This link is invalid or expired. Request a new link.'}</div>}
      {message && <div className="auth-success" role="status">{message}</div>}
      {mode === 'register' && <>
        <label className="field"><span>Display name</span><input autoComplete="name" required minLength={2} maxLength={80}
          value={name} onChange={e => setName(e.target.value)} disabled={busy} /></label>
        <label className="field"><span id="auth-username-label">Username</span><input autoComplete="username" required minLength={3} maxLength={32}
          aria-labelledby="auth-username-label"
          pattern="[A-Za-z][A-Za-z0-9_]{2,31}" aria-describedby="username-help"
          value={username} onChange={e => setUsername(e.target.value)} disabled={busy} />
          <small id="username-help">3–32 letters, numbers or underscores; start with a letter.</small></label>
      </>}
      {['register', 'resend', 'forgot'].includes(mode) && <label className="field"><span>Email</span>
        <input type="email" autoComplete="email" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} disabled={busy} />
      </label>}
      {withPassword && !invalidLink && <>
        <label className="field"><span id="auth-password-label">{mode === 'reset' ? 'New password' : 'Password'}</span>
          <span className="password-wrap">
            <input type={reveal ? 'text' : 'password'} autoComplete="new-password" required minLength={15} maxLength={128}
              aria-labelledby="auth-password-label" aria-describedby="password-help" value={password} onChange={e => setPassword(e.target.value)} disabled={busy} />
            <button type="button" className="icon-button" aria-label={reveal ? 'Hide password' : 'Show password'}
              onClick={() => setReveal(!reveal)}>{reveal ? <EyeOff size={18} /> : <Eye size={18} />}</button>
          </span><small id="password-help">15–128 characters. A few memorable words work well.</small>
        </label>
        <label className="field"><span>Confirm password</span>
          <input type={reveal ? 'text' : 'password'} autoComplete="new-password" required maxLength={128}
            value={confirmation} onChange={e => setConfirmation(e.target.value)} disabled={busy} />
        </label>
      </>}
      {!invalidLink && <button className="primary-button" type="submit" disabled={busy}>
        {busy ? 'Please wait…' : { register: 'Create account', resend: 'Resend verification link', forgot: 'Send reset link',
          verify: 'Verify email', reset: 'Update password' }[mode]}
      </button>}
      {['register', 'resend', 'forgot'].includes(mode) && <p className="auth-hint">Demo email stays on this computer. Open it with the local inbox command in the README; no real email is sent.</p>}
      <div className="auth-links">
        {(mode === 'verify' || mode === 'reset') && <button type="button" disabled={busy}
          onClick={() => navigate(mode === 'verify' ? 'resend' : 'forgot')}>
          {mode === 'verify' ? 'Request a new verification link' : 'Request a new reset link'}
        </button>}
        <button type="button" disabled={busy} onClick={() => navigate('login')}>Back to sign in</button>
      </div>
    </form>
  </AuthShell>;
}
