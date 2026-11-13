import { useEffect, useState } from 'react';
import {
  ArrowLeftRight, Bell, Check, Copy, CreditCard, Eye, EyeOff, FileText, History, Landmark, LayoutGrid, LifeBuoy,
  PiggyBank, QrCode, ReceiptText, Search, ShieldCheck, Sparkles, Target, TrendingUp, UserRound,
} from 'lucide-react';

import type { DemoUser, Profile } from '../../types';
import type { Tab } from '../app/NavBar';
import { MonthPulse, NewsTeaser, SafetyTip, UpcomingBills } from './Rail';
import { api } from '../../api';
import { greeting, initials, vnd } from '../../format';
import { navigate as go } from '../../router';
import { useResource } from '../explore/shared';

interface HomeProps {
  user: DemoUser;
  profile: Profile | null;
  navigate: (tab: Tab) => void;
  ask: (text: string) => void;
  transfer: () => void;
}

interface Summary { savings_principal_vnd: number; credit_debt_vnd: number; unpaid_bills: number }

// Each tile opens an existing Explore section; nothing here is a placeholder.
const SERVICES = [
  { label: 'Accounts', icon: Landmark, section: 'accounts' },
  { label: 'Cards', icon: CreditCard, section: 'cards' },
  { label: 'Savings', icon: PiggyBank, section: 'savings' },
  { label: 'Spending', icon: TrendingUp, section: 'insights' },
  { label: 'Goals', icon: Target, section: 'goals' },
  { label: 'Statements', icon: FileText, section: 'statements' },
  { label: 'Support', icon: LifeBuoy, section: 'support' },
  { label: 'All services', icon: LayoutGrid, section: '' },
];

export function Home({ user, profile, navigate, ask, transfer }: HomeProps) {
  // Hidden by default, as in banking apps: shoulder-surfing protection until the customer asks.
  const visibilityKey = `novabank-balance-visible:${user.id}`;
  const [shown, setShown] = useState(() => {
    try { return localStorage.getItem(visibilityKey) === 'true'; } catch { return false; }
  });
  const [copied, setCopied] = useState(false);
  const [unread, setUnread] = useState(0);
  const [query, setQuery] = useState('');
  const account = profile?.accounts[0];
  const name = profile?.name ?? user.name;
  const totalBalance = profile?.accounts.reduce((sum, item) => sum + item.balance_vnd, 0) ?? 0;
  const month = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' }).slice(0, 7);
  // Balance in the key refetches the summary after a transfer.
  const summary = useResource<Summary>(user, `/insights?month=${month}&revision=${account?.balance_vnd ?? 0}`).data;

  useEffect(() => {
    api.notifications(user).then(page => setUnread(page.unread_count)).catch(() => { });
  }, [user]);

  function toggleBalance() {
    const next = !shown;
    setShown(next);
    try { localStorage.setItem(visibilityKey, String(next)); } catch { /* Storage may be disabled. */ }
  }

  async function copyAccount() {
    if (!account) return;
    try {
      await navigator.clipboard.writeText(account.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard blocked: nothing to confirm */ }
  }

  const hidden = '••••••';
  const quick = [
    { label: 'Transfer', icon: ArrowLeftRight, run: transfer },
    { label: 'QR Pay', icon: QrCode, run: () => navigate('qr') },
    { label: 'Pay bills', icon: ReceiptText, run: () => go('/explore/bills'), badge: summary?.unpaid_bills },
    { label: 'History', icon: History, run: () => navigate('activity') },
  ];
  const services = SERVICES.map(s => ({ ...s, run: () => go(s.section ? '/explore/' + s.section : '/explore') }));
  // Search matches feature names; anything else becomes a question for Nova.
  const searchable = [...quick, ...services,
    { label: 'Notifications', icon: Bell, run: () => navigate('notifications') },
    { label: 'Profile & security', icon: UserRound, run: () => navigate('profile') }];
  const q = query.trim();
  const results = q ? searchable.filter(item => item.label.toLowerCase().includes(q.toLowerCase())) : [];

  return (
    <div className="page home with-rail">
      <div className="rail-main">
      <header className="home-top">
        <button className="home-profile" onClick={() => navigate('profile')} aria-label={`Open profile for ${name}`}>
          <span className="avatar home-avatar" aria-hidden="true">{initials(name)}<span className="home-verified"><ShieldCheck size={12} /></span></span>
          <span className="home-hello"><small>{greeting()}</small><strong>{name}</strong><small>@{user.id} · Verified</small></span>
        </button>
        <button className="home-round" aria-label={unread ? `Notifications, ${unread} unread` : 'Notifications'} onClick={() => navigate('notifications')}>
          <Bell size={20} aria-hidden="true" />
          {unread > 0 && <span className="count-badge" aria-hidden="true">{unread > 99 ? '99+' : unread}</span>}
        </button>
      </header>

      <form className="home-search" role="search" onSubmit={e => { e.preventDefault(); if (results[0]) results[0].run(); else if (q) ask(q); }}>
        <Search size={18} aria-hidden="true" />
        <input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search services or ask Nova"
          aria-label="Search services or ask Nova" autoComplete="off" />
        {q && (
          <ul className="search-results">
            {results.map(({ label, icon: Icon, run }) => (
              <li key={label}><button type="button" onClick={run}><Icon size={18} aria-hidden="true" />{label}</button></li>
            ))}
            <li><button type="button" onClick={() => ask(q)}><Sparkles size={18} aria-hidden="true" />Ask Nova: “{q}”</button></li>
          </ul>
        )}
      </form>

      <div className="home-grid">
        <section className="card wallet" aria-label="Payment account">
          <div className="wallet-head">
            <span>Total balance · {profile?.accounts.length ?? 0} payment account{profile?.accounts.length === 1 ? '' : 's'}</span>
            <button className="wallet-eye" onClick={toggleBalance} disabled={!account}
              aria-label={shown ? 'Hide balance' : 'Show balance'} aria-pressed={shown}>
              {shown ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {account
            ? <strong className={`balance ${shown ? 'is-shown' : ''}`} key={String(shown)}>{shown ? vnd(totalBalance) : `${hidden} VND`}</strong>
            : <span className="skeleton skeleton-balance" />}
          <div className="wallet-meta">
            {account && (
              <button className="account-no" onClick={copyAccount} aria-label={`Copy account number ${account.id}`}>
                {account.id} {copied ? <Check size={14} /> : <Copy size={14} />}
                <span className="copied" aria-live="polite">{copied ? 'Copied' : ''}</span>
              </button>
            )}
            <button className="wallet-stat" onClick={() => go('/explore/savings')}>
              <span>Savings</span><strong>{summary ? (shown ? vnd(summary.savings_principal_vnd) : hidden) : '—'}</strong>
            </button>
            <button className="wallet-stat" onClick={() => go('/explore/cards')}>
              <span>Credit used</span><strong>{summary ? (shown ? vnd(summary.credit_debt_vnd) : hidden) : '—'}</strong>
            </button>
          </div>
          <ul className="home-tiles home-quick">
            {quick.map(({ label, icon: Icon, run, badge }) => (
              <li key={label}>
                <button onClick={run} aria-label={badge ? `${label}, ${badge} unpaid` : label}>
                  <span className="tile-icon tile-quick">
                    <Icon size={22} aria-hidden="true" />
                    {!!badge && <span className="count-badge" aria-hidden="true">{badge}</span>}
                  </span>
                  <span>{label}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="card home-services" aria-labelledby="services-title">
          <h2 id="services-title" className="card-title">Services</h2>
          <ul className="home-tiles">
            {services.map(({ label, icon: Icon, run }) => (
              <li key={label}>
                <button onClick={run}>
                  <span className="tile-icon"><Icon size={22} aria-hidden="true" /></span>
                  <span>{label}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
      <aside className="side-rail" aria-label="At a glance">
        <MonthPulse user={user} />
        <UpcomingBills user={user} />
        <NewsTeaser user={user} />
        <SafetyTip />
      </aside>
    </div>
  );
}
