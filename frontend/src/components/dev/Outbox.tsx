import { useEffect, useState } from 'react';
import { request } from '../../api';

interface Mail { id: string; kind: string; recipient: string; created_at: number; expires_at: number | null }
interface Message extends Mail { message: string; code: string | null; action_url: string | null }

export function Outbox() {
  const [items, setItems] = useState<Mail[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [message, setMessage] = useState<Message | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    async function load() {
      try {
        const data = await request<{ items: Mail[] }>('/dev/outbox', undefined, { signal: controller.signal });
        if (alive) { setItems(data.items); setError(''); }
      } catch (e) { if (alive) setError((e as Error).message); }
    }
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => { alive = false; controller.abort(); clearInterval(timer); };
  }, []);
  useEffect(() => {
    setMessage(null);
    if (!selected) return;
    let alive = true;
    async function load() {
      try {
        const mail = await request<Message>('/dev/outbox/' + encodeURIComponent(selected!));
        if (alive) setMessage(mail);
      } catch (e) { if (alive) { setMessage(null); setError((e as Error).message); } }
    }
    void load();
    const timer = window.setInterval(() => void load(), 3000);
    return () => { alive = false; clearInterval(timer); };
  }, [selected]);
  return <main className="page" style={{ maxWidth: 960, margin: 'auto' }}>
    <h1 className="page-title">Demo inbox</h1>
    <p className="muted">Simulated email for this local demo. Open a message to read its verification code. Never send codes to the assistant.</p>
    <a href="/">Return to NovaBank</a>
    {error && <p className="form-error" role="alert">Demo inbox unavailable: {error}</p>}
    <div className="service-stack">
      <ul className="service-list" aria-label="Messages">{items.map(item => <li key={item.id}>
        <button className="link-button" aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}>
          {item.kind} · {item.recipient} · {new Date(item.created_at * 1000).toLocaleTimeString()}
        </button>
      </li>)}</ul>
      {message && <section className="card service-section" aria-label="Selected message">
        <h2>{message.kind}</h2><p>{message.message}</p>
        {message.code ? <p>Verification code: <strong data-testid="outbox-code">{message.code}</strong></p> : <p>No active verification code. It may have expired or already been used.</p>}
        {message.action_url && message.action_url.startsWith('/#') && <a href={message.action_url}>Open verification link</a>}
      </section>}
    </div>
  </main>;
}
