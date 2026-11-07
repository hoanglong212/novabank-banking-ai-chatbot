import { useState, type FormEvent } from 'react';
import { ArrowUpRight, Eye, EyeOff } from 'lucide-react';
import { AuthHeading, AuthSubmit } from './AuthUi';

interface LoginProps {
  onLogin: (username: string, password: string) => Promise<void>;
  notice: string | null;
  success?: string | null;
  onNavigate?: (mode: 'register' | 'forgot' | 'resend') => void;
}

const DEMO_ACCOUNTS = [['alice', 'Alice@2026'], ['bob', 'Bob@2026']];

export function Login({ onLogin, notice, success, onNavigate }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onLogin(username.trim(), password);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
        <form className="auth-form" onSubmit={submit} noValidate aria-label="Sign in" aria-busy={busy}>
          <AuthHeading eyebrow="WELCOME BACK" title="Sign in" subtitle="Use your NovaBank account to continue." />
          {success && <div className="auth-success" role="status">{success}</div>}
          {(error || notice) && <div className="form-error" role="alert">{error || notice}</div>}
          <div className="auth-fields">
          <div className="auth-field">
            <label htmlFor="signin-username">Username</label>
            <input id="signin-username" name="username" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="Enter your username" required autoFocus />
          </div>
          <div className="auth-field">
            <div className="auth-field-heading">
              <label htmlFor="signin-password">Password</label>
              <button className="auth-text-button" type="button" disabled={busy || !onNavigate}
                onClick={() => onNavigate?.('forgot')}>Forgot password?</button>
            </div>
            <div className="auth-password">
              <input id="signin-password" name="password" type={reveal ? 'text' : 'password'} autoComplete="current-password" value={password}
                onChange={e => setPassword(e.target.value)} placeholder="Enter your password" required />
              <button type="button" className="auth-reveal" aria-label={reveal ? 'Hide password' : 'Show password'} aria-pressed={reveal}
                onClick={() => setReveal(!reveal)}>
                {reveal ? <EyeOff size={19} aria-hidden="true" /> : <Eye size={19} aria-hidden="true" />}
              </button>
            </div>
          </div>
          </div>
          <AuthSubmit busy={busy} busyText="Signing in…" disabled={!username.trim() || !password}>Sign in</AuthSubmit>
          <p className="auth-switch">New around here? <button className="auth-text-button" type="button"
            disabled={busy || !onNavigate} onClick={() => onNavigate?.('register')}>Create an account</button></p>
          <section className="auth-demo" aria-labelledby="signin-demo-title">
            <div className="auth-demo-heading"><h2 id="signin-demo-title">Take a look around</h2><span>DEMO ACCOUNTS</span></div>
            <p>Choose a profile. We’ll fill in the details.</p>
            <div className="auth-demo-options">
            {DEMO_ACCOUNTS.map(([name, secret]) => (
              <button type="button" key={name} disabled={busy} onClick={() => { setUsername(name); setPassword(secret); }}>
                <span className="auth-avatar" aria-hidden="true">{name[0].toUpperCase()}</span>
                <span>{name[0].toUpperCase() + name.slice(1)}</span>
                <ArrowUpRight size={16} aria-hidden="true" />
              </button>
            ))}
            </div>
          </section>
          <p className="auth-verify-link">Already registered? <button className="auth-text-button" type="button"
            disabled={busy || !onNavigate} onClick={() => onNavigate?.('resend')}>Verify your email</button></p>
        </form>
  );
}
