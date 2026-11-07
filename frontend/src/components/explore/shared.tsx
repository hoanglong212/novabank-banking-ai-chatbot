import { KeyRound } from 'lucide-react';
import { cloneElement, useCallback, useEffect, useId, useRef, useState, type ReactElement } from 'react';
import { request, responseFor } from '../../api';
import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { PinForm } from '../profile/TransactionPin';
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
  const pending = useRef(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('');
  async function run(action: () => Promise<void>) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true); setError(''); setMessage('');
    try { await action(); } catch (e) { setError((e as Error).message); } finally { pending.current = false; setBusy(false); }
  }
  return { busy, error, message, setMessage, run };
}
export function Feedback({ state }: { state: { error: string; message: string } }) {
  return <>{state.error && <p role="alert" className="form-error">{state.error}</p>}{state.message && <p role="status" className="success-note">{state.message}</p>}</>;
}
export interface ActionDraft { challenge_id: string; kind: string; summary: Record<string, string | number>; expires_in: number; message: string; method?: 'totp' | 'pin' | 'email' }
export interface ActionResult { message: string; kind?: string; transaction_id?: string | null; sign_in_required?: boolean }
export function ConfirmAction({ user, draft, close, done }: { user: DemoUser; draft: ActionDraft | null; close: () => void; done: (result: ActionResult) => void }) {
  return <Sheet open={!!draft} title="Review and confirm" onClose={close}>{draft && <ConfirmForm key={draft.challenge_id} user={user} draft={draft} done={done} />}</Sheet>;
}
function ConfirmForm({ user, draft, done }: { user: DemoUser; draft: ActionDraft; done: (result: ActionResult) => void }) {
  const [code, setCode] = useState(''); const [key] = useState(() => crypto.randomUUID()); const op = useOperation();
  // Email and phone changes prove the new address with a code sent there; everything else uses the PIN.
  const [method, setMethod] = useState(draft.method ?? 'email');
  const contact = draft.kind === 'PROFILE_EMAIL' || draft.kind === 'PROFILE_PHONE';
  const labels: Record<string, string> = { account_id: 'Payment account', amount_vnd: 'Amount', resource_id: 'Reference', label: 'Description', term_months: 'Term (months)', value: 'New value', early_withdrawal_interest_vnd: 'Interest if withdrawn early', category: 'Category' };
  const titles: Record<string, string> = { FREEZE_CARD: 'Freeze your card', UNFREEZE_CARD: 'Unfreeze your card', CARD_PURCHASE: 'Review your purchase', REPAY_CARD: 'Repay your credit balance', PAY_BILL: 'Pay your bill', OPEN_SAVINGS: 'Open your savings deposit', WITHDRAW_SAVINGS: 'Withdraw your savings deposit' };
  // A div, not a form: the create-PIN step renders its own form and forms must not nest.
  return <div className="qr-form service-dialog">
    <h3>{titles[draft.kind] ?? draft.kind.replaceAll('_', ' ')}</h3>
    <dl className="detail-list">{Object.entries(draft.summary).map(([k, value]) => <div key={k}><dt>{labels[k] ?? k}</dt><dd>{k.endsWith('_vnd') ? vnd(Number(value)) : String(value)}</dd></div>)}</dl>
    {method === 'email' && !contact
      ? <div className="pin-first"><p className="otp-hint"><KeyRound size={18} aria-hidden="true" /><span><strong>Create your transaction PIN.</strong> These 6 digits confirm this and every future payment.</span></p>
        <PinForm user={user} submitLabel="Save PIN and continue" done={() => setMethod('pin')} /></div>
      : <form className="qr-form" onSubmit={e => { e.preventDefault(); void op.run(async () => {
        const result = await request<ActionResult>('/actions/confirm', user, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ challenge_id: draft.challenge_id, code }) }); done(result);
      }); }}>{method === 'email'
        ? <p className="muted">Enter the six-digit code sent to the new address. It expires in two minutes.</p>
        : <p className="otp-hint"><KeyRound size={18} aria-hidden="true" /><span>{method === 'totp' ? <>Open your <strong>authenticator app</strong> and enter the current six-digit NovaBank code.</> : <>Enter your <strong>6-digit transaction PIN</strong>.</>} Nothing changes until you confirm.</span></p>}
      <Feedback state={op} />
      <Field label={method === 'totp' ? 'Authenticator code' : method === 'pin' ? 'Transaction PIN' : 'Verification code'}><input autoFocus type={method === 'pin' ? 'password' : 'text'} inputMode="numeric" autoComplete={method === 'pin' ? 'off' : 'one-time-code'} pattern="[0-9]{6}" required maxLength={6} value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} /></Field>
      <button className="primary-button" disabled={op.busy || code.length !== 6}>{op.busy ? 'Confirming…' : 'Confirm action'}</button></form>}
  </div>;
}
export async function download(user: DemoUser, path: string, filename: string) {
  const blob = await (await responseFor(path, user)).blob();
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
