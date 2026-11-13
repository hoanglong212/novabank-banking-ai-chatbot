import { useEffect, useMemo, useState } from 'react';
import { Check, Copy, Inbox, RefreshCw } from 'lucide-react';
import { currentSession } from '../../sessionStore';
import '../../styles/outbox.css';

interface Mail { id: string; kind: string; recipient: string; created_at: number; expires_at: number | null }
interface Message extends Mail { message: string; code: string | null; action_url: string | null }

const LABELS: Record<string, string> = {
  LOGIN_OTP: 'Sign-in code', TRANSFER_OTP: 'Transfer OTP', VERIFY_EMAIL: 'Verify email',
  RESET_PASSWORD: 'Reset password', DISABLE_TOTP_OTP: 'Disable authenticator',
};
const label = (kind: string) => LABELS[kind] ?? kind.charAt(0) + kind.slice(1).replaceAll('_', ' ').toLowerCase();
const FILTER_KEY = 'outbox-kind'; // recipients are masked by the server, so filter by code type

const SESSION_KEY = 'novabank-session';
const CHALLENGE_POLL_MS = 300_000; // a sign-in challenge lives five minutes; polling longer only burns the server's rate limit
const SIGN_IN = 'Open the demo inbox from NovaBank: from the sign-in code screen, or from a signed-in tab.';

/** Opens the inbox in a new tab. Before sign-in, the challenge is the only key to that one sign-in code. */
export function openInbox(challenge?: string) {
  window.open('/outbox' + (challenge ? '#challenge=' + encodeURIComponent(challenge) : ''));
}

function takeChallenge() {
  const value = new URLSearchParams(window.location.hash.slice(1)).get('challenge');
  // Keep the challenge in memory only, out of the address bar and history.
  if (value) window.history.replaceState(null, '', window.location.pathname);
  return value;
}

type OpenerLike = { location: { origin: string }; sessionStorage: { getItem(key: string): string | null } };

/** The opener tab's access token, only when the opener is this same origin. Exported for tests. */
export function openerToken(self: { location: { origin: string }; opener: OpenerLike | null }): string | null {
  try {
    const opener = self.opener;
    // Explicit origin check: never read credentials from, or trust, a page on another origin that opened this tab.
    if (!opener || opener.location.origin !== self.location.origin) return null;
    const value: unknown = JSON.parse(opener.sessionStorage.getItem(SESSION_KEY) || 'null')?.token;
    return typeof value === 'string' && value ? value : null;
  } catch { return null; } // A cross-origin opener throws on location/storage access; a closed one may too.
}

function token() {
  // Opened from NovaBank: borrow that tab's current token. This tab never refreshes it, so it cannot rotate the session away.
  return openerToken(window as unknown as Parameters<typeof openerToken>[0]) ?? currentSession()?.accessToken ?? null;
}

async function inboxFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch('/api/dev' + path, { ...init, headers: { 'Content-Type': 'application/json', ...init.headers } });
  if (response.status === 401) throw new Error('Your NovaBank session is not active here. Return to NovaBank, then reopen the inbox.');
  if (!response.ok) {
    let reason = `Request failed (${response.status})`;
    try { const problem = await response.json(); if (typeof problem.detail === 'string') reason = problem.detail; } catch { /* ignore */ }
    throw new Error(reason);
  }
  return response.json() as Promise<T>;
}

function ago(seconds: number, now: number) {
  const s = Math.max(0, Math.round(now / 1000 - seconds));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.floor(s / 60)}m ago` : new Date(seconds * 1000).toLocaleTimeString();
}

export function Outbox() {
  const [items, setItems] = useState<Mail[]>([]);
  const [picked, setPicked] = useState<string | null>(null); // null = follow the newest message
  const [message, setMessage] = useState<Message | null>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [showExpired, setShowExpired] = useState(false);
  const [kind, setKind] = useState(() => { try { return localStorage.getItem(FILTER_KEY) ?? ''; } catch { return ''; } });
  const [challenge] = useState(takeChallenge);

  useEffect(() => {
    // The copied session belongs to the opener; a full load of NovaBank in this tab would reuse its refresh token.
    if (openerToken(window as unknown as Parameters<typeof openerToken>[0])) try { window.sessionStorage.removeItem(SESSION_KEY); } catch { /* storage blocked */ }
  }, []);

  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    async function load() {
      try {
        if (challenge) {
          const mail = await inboxFetch<Message>('/outbox/challenge', { method: 'POST', body: JSON.stringify({ challenge_id: challenge }), signal: controller.signal });
          if (alive) { setItems([mail]); setMessage(mail); setError(''); }
          return;
        }
        const bearer = token();
        if (!bearer) { if (alive) setError(SIGN_IN); return; }
        const data = await inboxFetch<{ items: Mail[] }>('/outbox', { headers: { Authorization: 'Bearer ' + bearer }, signal: controller.signal });
        if (alive) { setItems(data.items); setError(''); }
      } catch (e) { if (alive && !controller.signal.aborted) setError((e as Error).message); }
    }
    void load();
    const poll = window.setInterval(() => void load(), 3000);
    const stop = challenge ? window.setTimeout(() => clearInterval(poll), CHALLENGE_POLL_MS) : undefined;
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => { alive = false; controller.abort(); clearInterval(poll); clearTimeout(stop); clearInterval(tick); };
  }, [challenge]);

  const kinds = useMemo(() => [...new Set(items.map(i => i.kind))], [items]);
  const shown = useMemo(() => items.filter(i => (!kind || i.kind === kind) && (showExpired || !i.expires_at || i.expires_at * 1000 > now)), [items, kind, showExpired, now]);
  const newest = [...shown].sort((a, b) => b.created_at - a.created_at)[0];
  const selected = picked && shown.some(i => i.id === picked) ? picked : newest?.id ?? null;

  useEffect(() => {
    setCopied(false);
    if (challenge) return; // the list poll already carries the one challenge message
    if (!selected) { setMessage(null); return; }
    let alive = true;
    async function load() {
      try {
        const bearer = token();
        if (!bearer) throw new Error(SIGN_IN);
        const mail = await inboxFetch<Message>('/outbox/' + encodeURIComponent(selected!), { headers: { Authorization: 'Bearer ' + bearer } });
        if (alive) setMessage(mail);
      } catch (e) { if (alive) { setMessage(null); setError((e as Error).message); } }
    }
    void load();
    const timer = window.setInterval(() => void load(), 3000);
    return () => { alive = false; clearInterval(timer); };
  }, [selected, challenge]);

  useEffect(() => {
    const code = message?.id === selected ? message?.code : null;
    document.title = code ? `${code} · Demo inbox` : 'Demo inbox';
  }, [message, selected]);

  function chooseKind(value: string) {
    setKind(value); setPicked(null);
    try { localStorage.setItem(FILTER_KEY, value); } catch { /* per-viewer convenience only */ }
  }
  async function copy(code: string) {
    try { await navigator.clipboard.writeText(code); setCopied(true); window.setTimeout(() => setCopied(false), 2000); }
    catch { setError('Clipboard is blocked here. Select the code and copy it manually.'); }
  }

  const current = message && message.id === selected ? message : null;
  const left = current?.expires_at ? Math.max(0, Math.round(current.expires_at - now / 1000)) : null;
  return <main className="page outbox-page">
    <header className="outbox-head">
      <div><h1 className="page-title">Demo inbox</h1>
        <p className="muted">Simulated email for this local demo. Never send codes to the assistant.</p></div>
      <a className="secondary-button" href="/">Return to NovaBank</a>
    </header>
    {error && <p className="form-error" role="alert">Demo inbox: {error}</p>}

    <div className="outbox-toolbar">
      <label>Show{' '}
        <select value={kind} onChange={e => chooseKind(e.target.value)}>
          <option value="">All codes</option>
          {kinds.map(k => <option key={k} value={k}>{label(k)}</option>)}
        </select>
      </label>
      <label className="check-field"><input type="checkbox" checked={showExpired} onChange={e => setShowExpired(e.target.checked)} />Show expired</label>
      <span className="outbox-live"><RefreshCw size={14} aria-hidden="true" />Updates every 3 s</span>
      {picked && picked !== newest?.id && <button className="link-button" onClick={() => setPicked(null)}>Jump to newest</button>}
    </div>

    <div className="outbox-layout">
      <section className="card outbox-reader" aria-label="Selected message" aria-live="polite">
        {!current ? <p className="outbox-empty"><Inbox size={28} aria-hidden="true" />{shown.length ? 'Loading message…' : (showExpired ? 'No messages yet.' : 'No active codes.') + ' Request a code in the app and it appears here.'}</p> : <>
          <p className="outbox-meta">{label(current.kind)} · {current.recipient} · {ago(current.created_at, now)}</p>
          {current.code ? <>
            <button className="outbox-code" data-testid="outbox-code" onClick={() => void copy(current.code!)} aria-label={`Copy code ${current.code}`}>{current.code}</button>
            <div className="outbox-actions">
              <button className="primary-button" onClick={() => void copy(current.code!)}>{copied ? <><Check size={16} aria-hidden="true" />Copied</> : <><Copy size={16} aria-hidden="true" />Copy code</>}</button>
              {left !== null && <span className={left < 60 ? 'outbox-expiry is-soon' : 'outbox-expiry'}>{left ? `Expires in ${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` : 'Expired'}</span>}
            </div>
          </> : <p className="muted">No active code. It may have expired or already been used.</p>}
          {current.action_url && current.action_url.startsWith('/#') && <a className="primary-button" href={current.action_url}>Open verification link</a>}
          <details><summary>Full message</summary><p>{current.message}</p></details>
        </>}
      </section>

      <ul className="outbox-list" aria-label="Messages">{shown.map(item => <li key={item.id}>
        <button aria-pressed={selected === item.id} onClick={() => setPicked(item.id)}>
          <strong>{label(item.kind)}</strong>{item.id === newest?.id && <span className="outbox-new">Newest</span>}
          <small>{item.recipient} · {ago(item.created_at, now)}</small>
        </button>
      </li>)}</ul>
    </div>
  </main>;
}
