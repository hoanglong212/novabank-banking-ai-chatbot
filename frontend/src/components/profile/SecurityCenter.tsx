import { useCallback, useEffect, useRef, useState } from 'react';
import { Monitor, ShieldCheck } from 'lucide-react';
import { api } from '../../api';
import type { DemoUser, LoginAttempt, MfaStatus, Page, UserSession } from '../../types';
import { Pagination } from '../ui/Pagination';
import { AuthenticatorSettings } from './AuthenticatorSettings';

const moment = (seconds: number) => new Date(seconds * 1000).toLocaleString('en-GB', {
  timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'medium', timeStyle: 'short',
});
const results: Record<string, string> = { SUCCESS: 'Successful sign-in', PASSWORD_FAILED: 'Incorrect password',
  MFA_FAILED: 'Incorrect verification code', LOCKED: 'Temporarily locked' };

export function SecurityCenter({ user }: { user: DemoUser }) {
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [history, setHistory] = useState<Page<LoginAttempt> | null>(null);
  const [mfa, setMfa] = useState<MfaStatus | null>(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(true);
  const [changing, setChanging] = useState(false);
  const [confirm, setConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const request = useRef(0);
  const reload = useCallback(async () => {
    const id = ++request.current;
    setBusy(true); setError(null);
    try {
      const [active, attempts, factor] = await Promise.all([api.sessions(user), api.loginHistory(user, offset), api.mfaStatus(user)]);
      if (id === request.current) { setSessions(active.items); setHistory(attempts); setMfa(factor); }
    } catch (err) { if (id === request.current) setError((err as Error).message); }
    finally { if (id === request.current) setBusy(false); }
  }, [user, offset]);
  useEffect(() => { void reload(); return () => { request.current++; }; }, [reload]);

  async function revoke(id: string) {
    if (changing) return;
    setChanging(true); setError(null); setMessage(null);
    try {
      await api.revokeSession(user, id);
      setConfirm(null); setMessage('The other session has been signed out.');
      await reload();
    } catch (err) { setError((err as Error).message); }
    finally { setChanging(false); }
  }

  return <section className="security-center" aria-labelledby="security-title">
    <div className="page-heading"><div>
      <h2 id="security-title">Security Center</h2>
      <p className="muted small">Manage sign-ins and the devices with access to your account.</p>
    </div><button className="secondary-button" disabled={busy || changing} onClick={() => void reload()}>Refresh security</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {message && <p className="auth-success" role="status">{message}</p>}
    {busy && !history && <p className="muted" role="status">Loading security settings…</p>}

    <section className="card security-section" aria-labelledby="verification-title">
      <div className="security-heading"><ShieldCheck size={20} aria-hidden="true" /><h3 id="verification-title">Sign-in verification</h3></div>
      {mfa && <AuthenticatorSettings user={user} status={mfa} changed={text => { setMessage(text); void reload(); }} />}
    </section>

    <section className="card security-section" aria-labelledby="sessions-title" aria-busy={busy || changing}>
      <div className="security-heading"><Monitor size={20} aria-hidden="true" /><h3 id="sessions-title">Active sessions</h3></div>
      <p className="muted small">Sessions end after 5 minutes without activity or 8 hours after sign-in. Times below use Vietnam time.</p>
      <ul className="session-list">{sessions.map(item => <li className="session-row" key={item.id}>
        <div className="session-summary"><strong>{item.current ? 'This session' : 'Other session'}</strong>
          <span className="muted small">{item.method === 'totp' ? 'Authenticator' : 'Email code'} · {item.ip}</span></div>
        <span className="small">Last active {moment(item.last_active_at)}</span>
        <details><summary>Device details</summary><p className="muted small">{item.user_agent || 'Device information unavailable'}</p>
          <p className="muted small">Signed in {moment(item.created_at)} · Ends {moment(item.absolute_expires_at)}</p></details>
        {!item.current && (confirm === item.id ? <div className="session-confirm">
          <p className="small">Sign out this session? It will need a password and verification code to return.</p>
          <div className="inline-actions"><button className="danger-button" disabled={changing} onClick={() => void revoke(item.id)}>Confirm sign out</button>
            <button className="secondary-button" disabled={changing} onClick={() => setConfirm(null)}>Cancel</button></div>
        </div> : <button className="secondary-button" disabled={changing || busy} onClick={() => setConfirm(item.id)}>Sign out session</button>)}
      </li>)}</ul>
      {!busy && sessions.length === 0 && <p className="muted">No active sessions found.</p>}
    </section>

    <section className="card security-section" aria-labelledby="login-history-title" aria-busy={busy}>
      <h3 id="login-history-title">Login history</h3>
      <ul className="login-history">{history?.items.map(item => <li key={item.id}>
        <div className="session-summary"><strong>{results[item.result] || 'Sign-in attempt'}</strong><time dateTime={new Date(item.created_at * 1000).toISOString()}>{moment(item.created_at)}</time></div>
        <span className="muted small">{item.ip} · {item.method === 'totp' ? 'Authenticator' : item.method === 'email' ? 'Email code' : 'Password'}</span>
        <details><summary>Device details</summary><p className="muted small">{item.user_agent || 'Device information unavailable'}</p></details>
      </li>)}</ul>
      {history && <Pagination offset={history.offset} limit={history.limit} total={history.total} busy={busy} change={setOffset} />}
    </section>
  </section>;
}
