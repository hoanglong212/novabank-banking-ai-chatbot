import { useState } from 'react';
import { CreditCard, LockKeyhole, UnlockKeyhole, ShoppingBag, ArrowUpRight } from 'lucide-react';
import type { DemoUser } from '../../types';
import { vnd } from '../../format';
import { ConfirmAction, Feedback, Field, Loading } from './shared';
import { EmptyState, ServiceHeading, ServiceNote, displayDate } from './ServiceUi';
import { Sheet } from '../ui/Sheet';
import { useProducts } from './useProducts';

interface Card { id: string; kind: string; last_four: string; status: string; credit_limit_vnd: number; outstanding_vnd: number; transactions: { id: string; kind: string; merchant: string; amount_vnd: number; created_at: string }[] }
export function Cards({ user }: { user: DemoUser }) {
  const p = useProducts<Card>(user, 'cards');
  const [action, setAction] = useState<{ card: Card; kind: 'CARD_PURCHASE' | 'REPAY_CARD' } | null>(null);
  return <div className="service-stack"><ServiceHeading eyebrow="A CARD FOR EVERY DAY" title="Your Nova cards">Keep control of purchases, credit and card access.</ServiceHeading><Loading state={p.state} /><Feedback state={{ error: action ? '' : p.op.error, message: p.op.message }} />
    <div className="service-grid">{p.state.data?.items.map(card => <article className="product-card" key={card.id}>
      <div className={`bank-card ${card.kind.toLowerCase()}`}><div className="service-toolbar"><span>nova / {card.kind.toLowerCase()}</span><CreditCard size={25} strokeWidth={1.3} /></div><p className="card-number">•••• •••• •••• {card.last_four}</p><div className="service-toolbar"><small>{user.name.toUpperCase()}</small><span className="badge">{card.status.toLowerCase()}</span></div></div>
      <h2>Nova {card.kind.toLowerCase()}</h2>
      {card.kind === 'CREDIT' ? <dl className="detail-list"><div><dt>Outstanding</dt><dd>{vnd(card.outstanding_vnd)}</dd></div><div><dt>Available credit</dt><dd>{vnd(card.credit_limit_vnd - card.outstanding_vnd)}</dd></div><div><dt>Credit limit</dt><dd>{vnd(card.credit_limit_vnd)}</dd></div></dl> : <p className="service-hint">Purchases are paid directly from your linked payment account.</p>}
      <div className="service-actions"><button className="secondary-button" disabled={p.op.busy} onClick={() => p.prepare({ kind: card.status === 'ACTIVE' ? 'FREEZE_CARD' : 'UNFREEZE_CARD', resource_id: card.id })}>{card.status === 'ACTIVE' ? <LockKeyhole size={16} /> : <UnlockKeyhole size={16} />}{card.status === 'ACTIVE' ? 'Freeze card' : 'Unfreeze card'}</button><button className="primary-button" disabled={p.op.busy || card.status !== 'ACTIVE'} onClick={() => setAction({ card, kind: 'CARD_PURCHASE' })}><ShoppingBag size={16} />Simulate purchase</button></div>
      {card.status === 'FROZEN' && <p className="service-hint">Purchases are paused. Unfreeze your card to use it again.</p>}
      {card.kind === 'CREDIT' && <button className="link-button" disabled={p.op.busy || card.outstanding_vnd === 0} onClick={() => setAction({ card, kind: 'REPAY_CARD' })}>Repay credit balance<ArrowUpRight size={15} /></button>}
      <details><summary>Card history ({card.transactions.length})</summary>{!card.transactions.length && <p className="service-hint">Your next purchase will appear here.</p>}<ul className="service-list">{card.transactions.map(t => <li key={t.id}><div><strong>{t.merchant}</strong><small>{displayDate(t.created_at)} · {t.kind === 'REPAY_CARD' ? 'Repayment' : 'Purchase'}</small></div><span>{vnd(t.amount_vnd)}</span></li>)}</ul></details>
    </article>)}</div>
    {!p.state.busy && p.state.data?.items.length === 0 && <EmptyState title="No cards yet">Your demo cards will appear here once available.</EmptyState>}
    <ServiceNote>Cards and purchases are simulated. Card changes and payments require your verification code.</ServiceNote>
    <Sheet open={!!action} title={action?.kind === 'REPAY_CARD' ? 'Repay credit balance' : 'Simulate a purchase'} onClose={() => setAction(null)}>{action && <div className="service-dialog"><p>Nova {action.card.kind.toLowerCase()} · ending {action.card.last_four}</p>{action.kind === 'REPAY_CARD' && <div className="service-amount-preview"><span>Outstanding balance</span><strong>{vnd(action.card.outstanding_vnd)}</strong></div>}<Feedback state={p.op} /><form className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); p.prepare({ kind: action.kind, resource_id: action.card.id, amount_vnd: Number(data.get('amount')), label: data.get('label') }); }}><Field label="Amount (VND)"><input name="amount" type="number" min={1000} max={action.kind === 'REPAY_CARD' ? Math.min(action.card.outstanding_vnd, 100000000) : 100000000} step={1000} required defaultValue={action.kind === 'REPAY_CARD' ? action.card.outstanding_vnd : undefined} /></Field><Field label="Merchant or description"><input name="label" maxLength={120} required defaultValue={action.kind === 'REPAY_CARD' ? 'Credit repayment' : undefined} placeholder="Demo coffee shop" /></Field><button className="primary-button" disabled={p.op.busy}>Review action<ArrowUpRight size={16} /></button></form></div>}</Sheet>
    <ConfirmAction user={user} draft={p.draft} close={() => p.setDraft(null)} done={result => { setAction(null); p.complete(result); }} />
  </div>;
}
