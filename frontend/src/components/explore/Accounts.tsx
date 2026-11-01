import { useState } from 'react';
import type { DemoUser, TransferStart } from '../../types';
import { vnd } from '../../format';
import { Feedback, Field, Loading, send, useOperation, useResource } from './shared';

interface Account { id: string; nickname: string; holder_name: string; balance_vnd: number; status: string }
interface Beneficiary { id: string; bank: string; account_id: string; holder_name: string; nickname: string }
export function Accounts({ user, pay }: { user: DemoUser; pay: (start: TransferStart) => void }) {
  const [search, setSearch] = useState(''); const [editing, setEditing] = useState<string | null>(null);
  const accounts = useResource<{ items: Account[] }>(user, '/customer/accounts'); const people = useResource<{ items: Beneficiary[] }>(user, '/customer/beneficiaries?q=' + encodeURIComponent(search)); const op = useOperation();
  return <div className="service-stack"><Feedback state={op} /><section><h2 className="section-label">Your accounts</h2><Loading state={accounts} />
    <div className="service-grid">{accounts.data?.items.map(a => <article className="card service-section" key={a.id}><span className="badge">{a.status.toLowerCase()}</span><h3>{a.nickname}</h3><strong className="service-amount">{vnd(a.balance_vnd)}</strong><p>{a.holder_name}<br /><span className="muted">{a.id}</span></p>
      <form className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/customer/accounts/' + a.id, { nickname: data.get('nickname') }, 'PATCH'); accounts.reload(); op.setMessage('Nickname saved.'); }); }}>
        <Field label="Account nickname"><input name="nickname" defaultValue={a.nickname} maxLength={80} required /></Field><button className="secondary-button" disabled={op.busy}>Save nickname</button>
      </form></article>)}</div></section>
    <section className="card service-section"><h2 className="card-title">Saved recipients</h2><Loading state={people} />
      <Field label="Search saved recipients"><input type="search" value={search} maxLength={100} onChange={e => setSearch(e.target.value)} /></Field>
      {!people.busy && !people.data?.items.length && <p className="muted">Save someone you pay regularly. NovaBank verifies internal account names.</p>}
      <ul className="service-list">{people.data?.items.map(p => <li key={p.id}><div><strong>{p.nickname}</strong><small>{p.holder_name} · {p.bank}<br />{p.account_id}</small></div>{editing === p.id ? <form className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/customer/beneficiaries/' + p.id, { nickname: data.get('nickname') }, 'PATCH'); setEditing(null); people.reload(); }); }}><Field label="Recipient nickname"><input name="nickname" defaultValue={p.nickname} maxLength={80} required /></Field><button className="secondary-button" disabled={op.busy}>Save nickname</button><button type="button" className="link-button" onClick={() => setEditing(null)}>Cancel</button></form> : <div className="inline-actions"><button className="secondary-button" onClick={() => pay({ to_bank: p.bank, to_account: p.account_id, to_name: p.holder_name })}>Transfer</button><button className="link-button" disabled={op.busy} onClick={() => setEditing(p.id)}>Edit nickname</button><button className="link-button" disabled={op.busy} onClick={() => void op.run(async () => { await send(user, '/customer/beneficiaries/' + p.id, undefined, 'DELETE'); people.reload(); })}>Remove</button></div>}</li>)}</ul>
      <form className="service-form" onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const data = new FormData(form); void op.run(async () => { await send(user, '/customer/beneficiaries', Object.fromEntries(data)); form.reset(); people.reload(); op.setMessage('Recipient saved.'); }); }}>
        <h3>Add a recipient</h3><Field label="Bank"><select name="bank"><option>NovaBank</option><option>Demo Bank A</option><option>Demo Bank B</option></select></Field><Field label="Account ID or number"><input name="account_id" required maxLength={40} placeholder="ACC-BOB-001" /></Field><Field label="Nickname"><input name="nickname" required maxLength={80} /></Field><button className="primary-button" disabled={op.busy}>Verify and save recipient</button>
      </form></section></div>;
}
