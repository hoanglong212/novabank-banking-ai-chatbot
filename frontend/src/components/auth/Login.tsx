import { useState, type FormEvent } from 'react';
import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import { AuthShell } from './AuthShell';

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
    <AuthShell>
        <form className="login-card" onSubmit={submit} noValidate>
          <span className="brand-mark login-mark" aria-hidden="true">N</span>
          <h1>Sign in</h1>
          <p className="login-sub">Welcome back to NovaBank.</p>
          {success && <div className="auth-success" role="status">{success}</div>}
          {(error || notice) && <div className="form-error" role="alert">{error || notice}</div>}
          <label className="field">
            <span>Username</span>
            <input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="e.g. alice" required autoFocus />
          </label>
          <label className="field">
            <span>Password</span>
            <span className="password-wrap">
              <input type={reveal ? 'text' : 'password'} autoComplete="current-password" value={password}
                onChange={e => setPassword(e.target.value)} placeholder="Your password" required />
              <button type="button" className="icon-button" aria-label={reveal ? 'Hide password' : 'Show password'}
                onClick={() => setReveal(!reveal)}>
                {reveal ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
          <button className="primary-button" type="submit" disabled={busy || !username.trim() || !password}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          <div className="auth-links">
            <button type="button" disabled={busy} onClick={() => onNavigate?.('register')}>Create an account</button>
            <button type="button" disabled={busy} onClick={() => onNavigate?.('forgot')}>Forgot password?</button>
            <button type="button" disabled={busy} onClick={() => onNavigate?.('resend')}>Verify your email</button>
          </div>
          <div className="demo-accounts">
            <span><LockKeyhole size={14} aria-hidden="true" /> Demo accounts</span>
            {DEMO_ACCOUNTS.map(([name, secret]) => (
              <button type="button" key={name} disabled={busy} onClick={() => { setUsername(name); setPassword(secret); }}>
                {name} · {secret}
              </button>
            ))}
          </div>
        </form>
    </AuthShell>
  );
}
