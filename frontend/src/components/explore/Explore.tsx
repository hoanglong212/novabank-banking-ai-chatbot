import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowUpRight, Search, CreditCard, FileText, Landmark, LifeBuoy, PiggyBank, QrCode, ReceiptText, Target, TrendingUp } from 'lucide-react';
import type { DemoUser, TransferStart } from '../../types';
import { Accounts } from './Accounts';
import { Products } from './Products';
import { Goals, Insights, Statements } from './Insights';
import { Support } from './Support';
import { Knowledge } from './Knowledge';
import { QrStudio } from '../qr/QrStudio';
import { EmptyState } from './ServiceUi';
import '../../styles/explore.css';

const items = [
  { id: 'accounts', title: 'Accounts & recipients', text: 'Manage accounts and people you pay', icon: Landmark },
  { id: 'cards', title: 'Cards', text: 'Manage debit and credit cards', icon: CreditCard },
  { id: 'bills', title: 'Pay bills', text: 'Utilities, internet and mobile', icon: ReceiptText },
  { id: 'savings', title: 'Savings', text: 'Build your balance over time', icon: PiggyBank },
  { id: 'insights', title: 'Spending & budgets', text: 'See where your money goes', icon: TrendingUp },
  { id: 'goals', title: 'Goals & calculator', text: 'Plan for what comes next', icon: Target },
  { id: 'statements', title: 'Statements', text: 'Download PDF and CSV records', icon: FileText },
  { id: 'qr', title: 'Demo QR', text: 'Receive or scan a NovaBank code', icon: QrCode },
  { id: 'support', title: 'Help & support', text: 'Get help and follow your tickets', icon: LifeBuoy },
] as const;
type Section = typeof items[number]['id'];
const groups = [
  { title: 'Everyday essentials', text: 'A little less admin. A little more living.', ids: ['accounts', 'cards', 'bills', 'qr'] },
  { title: 'Make room for tomorrow', text: 'Give your money a plan to follow.', ids: ['savings', 'insights', 'goals'] },
  { title: 'Here when you need us', text: 'Your records, answers and a helping hand.', ids: ['statements', 'support'] },
];
export function Explore({ user, pay, initial, ticket }: { user: DemoUser; pay: (start: TransferStart) => void; initial?: string; ticket?: string }) {
  const [section, setSection] = useState<Section | null>(() => items.find(i => i.id === initial)?.id ?? null);
  const [query, setQuery] = useState('');
  const found = items.filter(item => `${item.title} ${item.text}`.toLowerCase().includes(query.toLowerCase().trim()));
  useEffect(() => { document.getElementById('main')?.scrollTo(0, 0); }, [section]);
  return <div className={`page explore-page${section ? ' is-service' : ''}`}>
    <header className="explore-heading"><div>{section ? <button className="link-button" onClick={() => setSection(null)}><ArrowLeft size={16} />All services</button> : <p className="service-eyebrow">A LITTLE MORE POSSIBILITY</p>}<h1>{items.find(i => i.id === section)?.title ?? 'More from your money.'}</h1><p>{section ? items.find(i => i.id === section)?.text : 'Everyday essentials. Bigger plans. All right here.'}</p></div>{!section && <span className="explore-monogram" aria-hidden="true">N</span>}</header>
    {!section && <><label className="explore-search"><Search size={20} /><input type="search" aria-label="Search services" placeholder="What would you like to do?" value={query} onChange={event => setQuery(event.target.value)} /><span>{found.length} services</span></label>
      {groups.map(group => { const visible = found.filter(item => group.ids.includes(item.id)); return visible.length > 0 && <section className="explore-group" key={group.title}><div className="explore-group-heading"><h2>{group.title}</h2><p>{group.text}</p></div><div className="explore-directory">{visible.map(({ id, title, text, icon: Icon }) => <button className={`explore-service explore-service-${id}`} key={id} onClick={() => setSection(id)}><span className="explore-service-icon"><Icon size={24} strokeWidth={1.5} /></span><span><strong>{title}</strong><small>{text}</small></span><ArrowUpRight size={19} className="explore-service-arrow" /></button>)}</div></section>; })}
      {!found.length && <EmptyState title="No matching service">Try “cards”, “savings”, “bills” or “support”.</EmptyState>}
      <footer className="explore-footer"><span>NovaBank services</span><span>Built around your everyday.</span></footer></>}
    {section === 'accounts' && <Accounts user={user} pay={pay} />}
    {(section === 'cards' || section === 'bills' || section === 'savings') && <Products key={section} user={user} section={section} />}
    {section === 'insights' && <Insights user={user} />}{section === 'goals' && <Goals user={user} />}{section === 'statements' && <Statements user={user} />}
    {section === 'support' && <div className="service-stack"><Support user={user} ticket={ticket} /><Knowledge user={user} /></div>}{section === 'qr' && <QrStudio user={user} pay={pay} />}
  </div>;
}
