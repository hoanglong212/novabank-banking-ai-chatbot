import { useState } from 'react';
import { Copy, Pencil, Plus, ArrowUpRight } from 'lucide-react';
import type { Bank, DemoUser, TransferStart } from '../../types';
import { vnd } from '../../format';
import { Feedback, Field, Loading, send, useOperation, useResource } from './shared';
import { ConfirmRemove, EmptyState, ServiceHeading, ServiceNote } from './ServiceUi';
import { Sheet } from '../ui/Sheet';

interface Account { id: string; nickname: string; holder_name: string; balance_vnd: number; status: string }
interface Beneficiary { id: string; bank: string; account_id: string; holder_name: string; nickname: string }
export function Accounts({ user, pay }: { user: DemoUser; pay: (start: TransferStart) => void }) {
  const accounts = useResource<{ items: Account[] }>(user, '/customer/accounts');
  const people = useResource<{ items: Beneficiary[] }>(user, '/customer/beneficiaries');
  const banks = useResource<Bank[]>(user, '/vietqr/banks');
  const op = useOperation();
  const [search, setSearch] = useState(''), [adding, setAdding] = useState(false), [bank, setBank] = useState('NovaBank');
  const [editing, setEditing] = useState<Beneficiary | null>(null), [rename, setRename] = useState<Account | null>(null), [removing, setRemoving] = useState<Beneficiary | null>(null);
  const matches = people.data?.items.filter(person => `${person.nickname} ${person.holder_name} ${person.bank} ${person.account_id}`.toLowerCase().includes(search.toLowerCase()));
  const modalError = <Feedback state={{ error: op.error, message: '' }} />;
  return <div className="service-stack">
    <Feedback state={{ error: adding || editing || rename || removing ? '' : op.error, message: op.message }} />
    <ServiceHeading eyebrow="YOUR MONEY, AT A GLANCE" title="Your accounts">Your balances and payment details, always close at hand.</ServiceHeading>
    <Loading state={accounts} />
    <div className="service-grid">{accounts.data?.items.map(a => <article className="account-surface" key={a.id}>
      <div className="service-toolbar"><h3>{a.nickname}</h3><span className={`service-status ${a.status.toLowerCase()}`}>{a.status.toLowerCase()}</span></div>
      <div><p className="service-hint">Available balance</p><strong className="service-amount">{vnd(a.balance_vnd)}</strong></div>
      <div className="account-details"><div>{a.holder_name}<br />{a.id}</div><button className="icon-button" aria-label={`Copy account ${a.id}`} onClick={() => void op.run(async () => { await navigator.clipboard.writeText(a.id); op.setMessage('Account number copied.'); })}><Copy size={18} /></button></div>
      <button className="link-button" onClick={() => setRename(a)}><Pencil size={14} /> Rename account</button>
    </article>)}</div>
    {!accounts.busy && accounts.data?.items.length === 0 && <EmptyState title="No payment accounts">Your payment accounts will appear here when available.</EmptyState>}
    <section className="card service-section"><ServiceHeading title="People you pay" action={<button className="primary-button" onClick={() => { setBank('NovaBank'); setAdding(true); }}><Plus size={17} />Add a recipient</button>}>Save their details once. Find them here next time.</ServiceHeading>
      <Loading state={people} /><Field label="Search saved recipients"><input type="search" value={search} maxLength={100} placeholder="Name, bank or account number" onChange={e => setSearch(e.target.value)} /></Field>
      {!people.busy && !people.error && !matches?.length && <EmptyState title={search ? 'No matching recipients' : 'Your circle starts here'}>{search ? 'Try another name or account number.' : 'Add a recipient to make your next transfer easier.'}</EmptyState>}
      <ul className="service-list">{matches?.map(p => <li key={p.id}><div className="recipient-person"><span className="recipient-avatar" aria-hidden="true">{p.nickname.slice(0, 2).toUpperCase()}</span><div><strong>{p.nickname}</strong><small>{p.holder_name} · {p.bank}<br />{p.account_id}</small></div></div><div className="inline-actions"><button className="secondary-button" onClick={() => pay({ to_bank: p.bank, to_account: p.account_id, to_name: p.holder_name })}>Transfer<ArrowUpRight size={15} /></button><button className="link-button" disabled={op.busy} onClick={() => setEditing(p)}>Edit nickname</button><button className="link-button" disabled={op.busy} onClick={() => setRemoving(p)}>Remove</button></div></li>)}</ul>
    </section>
    <ServiceNote>NovaBank account names are verified locally. Other-bank recipient names are simulated for this demo.</ServiceNote>
    <Sheet open={adding} title="Add a recipient" onClose={() => setAdding(false)}><div className="service-dialog"><p>Choose a bank and save the account details for future transfers.</p>{modalError}<Loading state={banks} /><form className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/customer/beneficiaries', Object.fromEntries(data)); setAdding(false); people.reload(); op.setMessage('Recipient saved.'); }); }}>
      <Field label="Bank"><select name="bank" value={bank} onChange={e => setBank(e.target.value)}><option value="NovaBank">NovaBank</option>{banks.data?.filter(b => b.shortName !== 'NovaBank').map(b => <option key={b.bin} value={b.shortName}>{b.shortName}</option>)}</select></Field>
      <Field label="Account ID or number"><input name="account_id" key={bank} required maxLength={40} pattern={bank === 'NovaBank' ? 'ACC-[A-Za-z0-9-]{3,30}' : '[0-9]{6,19}'} placeholder={bank === 'NovaBank' ? 'ACC-BOB-001' : '6–19 digits'} /></Field><Field label="Nickname"><input name="nickname" required maxLength={80} placeholder="A name you will recognise" /></Field><button className="primary-button" disabled={op.busy}>{op.busy ? 'Saving…' : 'Verify and save recipient'}</button>
    </form></div></Sheet>
    <Sheet open={!!editing || !!rename} title={rename ? 'Rename account' : 'Edit recipient'} onClose={() => { setEditing(null); setRename(null); }}><div className="service-dialog">{modalError}<form key={rename?.id ?? editing?.id} className="service-form" onSubmit={e => { e.preventDefault(); const nickname = new FormData(e.currentTarget).get('nickname'); void op.run(async () => { await send(user, rename ? '/customer/accounts/' + rename.id : '/customer/beneficiaries/' + editing!.id, { nickname }, 'PATCH'); setRename(null); setEditing(null); accounts.reload(); people.reload(); op.setMessage('Nickname saved.'); }); }}><Field label={rename ? 'Account nickname' : 'Recipient nickname'}><input name="nickname" defaultValue={rename?.nickname ?? editing?.nickname} maxLength={80} required /></Field><button className="primary-button" disabled={op.busy}>Save nickname</button></form></div></Sheet>
    <ConfirmRemove title="Remove recipient?" open={!!removing} close={() => setRemoving(null)} busy={op.busy} action={() => void op.run(async () => { await send(user, '/customer/beneficiaries/' + removing!.id, undefined, 'DELETE'); setRemoving(null); people.reload(); op.setMessage('Recipient removed.'); })}>Remove {removing?.nickname} from saved recipients? Their previous transactions stay in your history.{modalError}</ConfirmRemove>
  </div>;
}