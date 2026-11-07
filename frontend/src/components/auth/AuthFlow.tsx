import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Eye, EyeOff, KeyRound, Mail, MailCheck, UserRoundPlus } from 'lucide-react';
import { api } from '../../api';
import { AuthShell } from './AuthShell';
import { Login } from './Login';
import type { AuthLink } from './authLink';
import type { LoginResponse, MfaChallenge } from '../../types';
import { MfaSignIn } from './MfaSignIn';
import { AuthBack, AuthHeading, AuthSubmit } from './AuthUi';

type Mode = 'login' | 'register' | 'resend' | 'forgot' | 'verify' | 'reset';
const titles: Record<Mode, string> = { login: 'Sign in', register: 'Create account', resend: 'Verify your email',
  forgot: 'Forgot password?', verify: 'Verify your email', reset: 'Choose a new password' };
const subtitles: Record<Mode, string> = { login: '', register: 'Start with a free, zero-balance demo account.',
  resend: 'Open the verification link in the local demo inbox.', forgot: 'We’ll help you get back into your demo account.',
  verify: 'Confirm your email to open your demo account.', reset: 'Reset links work once and expire after 15 minutes.' };

export function AuthFlow({ onLogin, onVerified, notice, link, onReplayIntro }: {
  onLogin: (username: string, password: string) => Promise<MfaChallenge | LoginResponse>;
  onVerified: (session: LoginResponse) => void; notice: string | null; link: AuthLink | null;
  onReplayIntro?: () => void;
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

  return <AuthShell stage={challenge ? 'mfa' : mode} onReplayIntro={mode === 'login' && !challenge ? onReplayIntro : undefined}>
  {challenge ? <MfaSignIn challenge={challenge} complete={onVerified} cancel={() => setChallenge(null)} />
  : mode === 'login' ? <Login onLogin={async (username, password) => {
    const result = await onLogin(username, password);
    if (!alive.current) return;
    if ('access_token' in result) onVerified(result);
    else setChallenge(result);
  }} notice={notice} success={message} onNavigate={navigate} />
  : <form className={`auth-form auth-form-${mode}`} onSubmit={submit} aria-busy={busy}>
      <AuthBack disabled={busy} onClick={() => navigate('login')} />
      <AuthHeading headingRef={heading} title={titles[mode]} subtitle={subtitles[mode]}
        eyebrow={mode === 'register' ? 'A FRESH START' : mode === 'reset' || mode === 'forgot' ? 'LET’S GET YOU BACK IN' : 'ONE MORE LITTLE STEP'}
        icon={mode === 'register' ? UserRoundPlus : mode === 'reset' || mode === 'forgot' ? KeyRound : mode === 'verify' ? MailCheck : Mail} />
      {(error || invalidLink) && <div className="form-error" role="alert">{error || 'This link is invalid or expired. Request a new link.'}</div>}
      {message && <div className="auth-success" role="status">{message}</div>}
      <div className={`auth-fields ${mode === 'register' ? 'auth-register-grid' : ''}`}>
      {mode === 'register' && <>
        <label className="auth-field"><span>Display name</span><input autoComplete="name" required minLength={2} maxLength={80} placeholder="Your name"
          value={name} onChange={e => setName(e.target.value)} disabled={busy} /></label>
        <label className="auth-field"><span id="auth-username-label">Username</span><input autoComplete="username" required minLength={3} maxLength={32} placeholder="Choose a username"
          aria-labelledby="auth-username-label"
          pattern="[A-Za-z][A-Za-z0-9_]{2,31}" aria-describedby="username-help"
          value={username} onChange={e => setUsername(e.target.value)} disabled={busy} />
          <small id="username-help">3–32 letters, numbers or underscores; start with a letter.</small></label>
      </>}
      {['register', 'resend', 'forgot'].includes(mode) && <label className="auth-field auth-field-wide"><span>Email</span>
        <input type="email" autoComplete="email" required maxLength={254} placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} disabled={busy} />
      </label>}
      {withPassword && !invalidLink && <>
        <label className="auth-field"><span id="auth-password-label">{mode === 'reset' ? 'New password' : 'Password'}</span>
          <span className="auth-password">
            <input type={reveal ? 'text' : 'password'} autoComplete="new-password" required minLength={15} maxLength={128}
              aria-labelledby="auth-password-label" aria-describedby="password-help" value={password} onChange={e => setPassword(e.target.value)} disabled={busy} />
            <button type="button" className="auth-reveal" aria-label={reveal ? 'Hide password' : 'Show password'} aria-pressed={reveal}
              onClick={() => setReveal(!reveal)}>{reveal ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}</button>
          </span><small id="password-help">15–128 characters. A few memorable words work well.</small>
        </label>
        <label className="auth-field"><span>Confirm password</span>
          <input type={reveal ? 'text' : 'password'} autoComplete="new-password" required maxLength={128}
            value={confirmation} onChange={e => setConfirmation(e.target.value)} disabled={busy} />
        </label>
      </>}
      </div>
      {!invalidLink && <AuthSubmit busy={busy}>
        {{ register: 'Create account', resend: 'Resend verification link', forgot: 'Send reset link',
          verify: 'Verify email', reset: 'Update password' }[mode]}
      </AuthSubmit>}
      {['register', 'resend', 'forgot'].includes(mode) && <p className="auth-local-note"><Mail size={15} aria-hidden="true" /><span>Demo emails stay in your local inbox. No real email is sent.</span></p>}
      <div className="auth-secondary-actions">
        {(mode === 'verify' || mode === 'reset') && <button type="button" disabled={busy}
          onClick={() => navigate(mode === 'verify' ? 'resend' : 'forgot')}>
          {mode === 'verify' ? 'Request a new verification link' : 'Request a new reset link'}
        </button>}
      </div>
    </form>}
  </AuthShell>;
}
