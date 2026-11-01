import { useEffect, useState } from 'react';
import { ArrowLeft, CreditCard, FileText, Landmark, LifeBuoy, PiggyBank, QrCode, ReceiptText, Target, TrendingUp } from 'lucide-react';
import type { DemoUser, TransferStart } from '../../types';
import { Accounts } from './Accounts';
import { Products } from './Products';
import { Goals, Insights, Statements } from './Insights';
import { Support } from './Support';
import { Knowledge } from './Knowledge';
import { QrStudio } from '../qr/QrStudio';

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
export function Explore({ user, pay }: { user: DemoUser; pay: (start: TransferStart) => void }) {
  const [section, setSection] = useState<Section | null>(null);
  useEffect(() => { document.getElementById('main')?.scrollTo(0, 0); }, [section]);
  return <div className="page"><div className="page-heading"><div>{section && <button className="link-button" onClick={() => setSection(null)}><ArrowLeft size={16} />All services</button>}<h1 className="page-title">{items.find(i => i.id === section)?.title ?? 'Explore'}</h1><p className="muted">{section ? items.find(i => i.id === section)?.text : 'Your everyday banking, in one place.'}</p></div></div>
    {!section && <div className="explore-grid">{items.map(({ id, title, text, icon: Icon }) => <button className="card explore-item" key={id} onClick={() => setSection(id)}><span className="row-icon"><Icon size={24} aria-hidden="true" /></span><strong>{title}</strong><span className="muted">{text}</span></button>)}</div>}
    {section === 'accounts' && <Accounts user={user} pay={pay} />}
    {(section === 'cards' || section === 'bills' || section === 'savings') && <Products key={section} user={user} section={section} />}
    {section === 'insights' && <Insights user={user} />}{section === 'goals' && <Goals user={user} />}{section === 'statements' && <Statements user={user} />}
    {section === 'support' && <div className="service-stack"><Support user={user} /><Knowledge user={user} /></div>}{section === 'qr' && <QrStudio user={user} pay={pay} />}
  </div>;
}
