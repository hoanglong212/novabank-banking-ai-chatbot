import { useState } from 'react';
import type { DemoUser } from '../../types';
import { ConfirmAction, Feedback, Field, Loading, send, useOperation, useResource, type ActionDraft } from '../explore/shared';

interface CustomerProfile { name: string; email: string; phone: string; kyc_status: string }
export function ProfileEditor({ user, logout }: { user: DemoUser; logout: () => void }) {
  const state = useResource<CustomerProfile>(user, '/customer/profile'); const op = useOperation();
  const [field, setField] = useState('name'); const [draft, setDraft] = useState<ActionDraft | null>(null);
  return <section className="card service-section"><h2 className="card-title">Personal details</h2><Loading state={state} />
    {state.data && <dl className="detail-list"><div><dt>Name</dt><dd>{state.data.name}</dd></div><div><dt>Email</dt><dd>{state.data.email}</dd></div><div><dt>Phone</dt><dd>{state.data.phone || 'Not added'}</dd></div><div><dt>Demo identity check</dt><dd>{state.data.kyc_status.toLowerCase()}</dd></div></dl>}
    <form className="service-form" onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const data = new FormData(form); void op.run(async () => {
      setDraft(await send<ActionDraft>(user, '/customer/profile/change', { field, value: data.get('value'), password: data.get('password') })); form.reset();
    }); }}>
      <Field label="Update"><select value={field} onChange={e => setField(e.target.value)}><option value="name">Display name</option><option value="email">Email</option><option value="phone">Phone</option><option value="password">Password</option></select></Field>
      <Field label={field === 'password' ? 'New password (15–128 characters)' : 'New value'}><input key={field} name="value" type={field === 'password' ? 'password' : field === 'email' ? 'email' : 'text'} minLength={field === 'password' ? 15 : 1} maxLength={field === 'password' ? 128 : 254} required autoComplete={field === 'password' ? 'new-password' : 'off'} /></Field>
      <Field label="Current password for profile change"><input name="password" type="password" autoComplete="current-password" required maxLength={128} /></Field>
      <Feedback state={op} /><button className="secondary-button" disabled={op.busy}>{op.busy ? 'Please wait…' : field === 'email' || field === 'phone' ? 'Send verification code' : 'Continue to verification'}</button>
    </form>
    <ConfirmAction user={user} draft={draft} close={() => setDraft(null)} done={result => { setDraft(null); if (result.sign_in_required) logout(); else { op.setMessage(result.message); state.reload(); } }} />
  </section>;
}
