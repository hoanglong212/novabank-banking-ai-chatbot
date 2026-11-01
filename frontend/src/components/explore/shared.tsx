import { cloneElement, useCallback, useEffect, useId, useState, type ReactElement } from 'react';
import { request, responseFor } from '../../api';
import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { Sheet } from '../ui/Sheet';

export function send<T>(user: DemoUser, path: string, body?: unknown, method = 'POST') {
  return request<T>(path, user, { method, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
}
export function useResource<T>(user: DemoUser, path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(n => n + 1), []);
  useEffect(() => {
    let active = true; setBusy(true); setError('');
    request<T>(path, user).then(value => { if (active) setData(value); })
      .catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [user, path, revision]);
  return { data, error, busy, reload };
}
export function Loading({ state }: { state: { busy: boolean; error: string; reload: () => void } }) {
  return <>{state.busy && <p role="status" className="muted">Loading…</p>}{state.error && <div role="alert" className="form-error">{state.error} <button className="link-button" onClick={state.reload}>Try again</button></div>}</>;
}
export function Field({ label, children }: { label: string; children: ReactElement<{ id?: string }> }) {
  const id = useId();
  return <div className="field"><label htmlFor={id}>{label}</label>{cloneElement(children, { id })}</div>;
}
export function useOperation() {
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try { await action(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return { busy, error, message, setMessage, run };
}
export function Feedback({ state }: { state: { error: string; message: string } }) {
  return <>{state.error && <p role="alert" className="form-error">{state.error}</p>}{state.message && <p role="status" className="success-note">{state.message}</p>}</>;
}
export interface ActionDraft { challenge_id: string; kind: string; summary: Record<string, string | number>; expires_in: number; message: string }
export interface ActionResult { message: string; transaction_id?: string | null; sign_in_required?: boolean }
export function ConfirmAction({ user, draft, close, done }: { user: DemoUser; draft: ActionDraft | null; close: () => void; done: (result: ActionResult) => void }) {
  return <Sheet open={!!draft} title="Review and confirm" onClose={close}>{draft && <ConfirmForm key={draft.challenge_id} user={user} draft={draft} done={done} />}</Sheet>;
}
function ConfirmForm({ user, draft, done }: { user: DemoUser; draft: ActionDraft; done: (result: ActionResult) => void }) {
  const [code, setCode] = useState(''); const [key] = useState(() => crypto.randomUUID()); const op = useOperation();
  const labels: Record<string, string> = { account_id: 'Payment account', amount_vnd: 'Amount', resource_id: 'Reference', label: 'Description', term_months: 'Term (months)', value: 'New value', early_withdrawal_interest_vnd: 'Interest if withdrawn early', category: 'Category' };
  return <form className="qr-form" onSubmit={e => { e.preventDefault(); void op.run(async () => {
    const result = await request<ActionResult>('/actions/confirm', user, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ challenge_id: draft.challenge_id, code }) }); done(result);
  }); }}>
    <p className="eyebrow">{draft.kind.replaceAll('_', ' ')}</p>
    <dl className="detail-list">{Object.entries(draft.summary).map(([k, value]) => <div key={k}><dt>{labels[k] ?? k}</dt><dd>{k.endsWith('_vnd') ? vnd(Number(value)) : String(value)}</dd></div>)}</dl>
    <p className="muted">Enter the six-digit code delivered to your demo email or phone. It expires in two minutes. Money moves only after you confirm.</p>
    <Feedback state={op} />
    <Field label="Verification code"><input autoFocus inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" required maxLength={6} value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} /></Field>
    <button className="primary-button" disabled={op.busy || code.length !== 6}>{op.busy ? 'Confirming…' : 'Confirm action'}</button>
  </form>;
}
export async function download(user: DemoUser, path: string, filename: string) {
  const blob = await (await responseFor(path, user)).blob();
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
