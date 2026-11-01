import { useState } from 'react';
import {
  ArrowDownLeft, ArrowLeftRight, ArrowUpRight, Check, ChevronRight, ClipboardList, Copy, CreditCard, Eye, EyeOff,
  MapPin, Percent, QrCode, ReceiptText, ShieldCheck,
} from 'lucide-react';

import type { DemoUser, Profile } from '../../types';
import type { Tab } from '../app/NavBar';
import { Overview } from './Overview';
import { greeting, vnd } from '../../format';

interface HomeProps {
  user: DemoUser;
  profile: Profile | null;
  navigate: (tab: Tab) => void;
  ask: (text: string) => void;
  transfer: () => void;
}

// Topics in the Nova panel open the assistant with the question already asked.
const TOPICS = [
  { label: 'Card services', icon: CreditCard, text: 'My card is blocked, what should I do?' },
  { label: 'Fees & limits', icon: Percent, text: 'What are the transfer fees and limits?' },
  { label: 'Transaction status', icon: ReceiptText, text: 'Check transaction TX-1002' },
  { label: 'Support ticket', icon: ClipboardList, text: 'Create a support ticket for my pending transaction' },
  { label: 'Branches & hours', icon: MapPin, text: 'What are your opening hours?' },
  { label: 'Security tips', icon: ShieldCheck, text: 'How do I protect myself from banking fraud?' },
];

export function Home({ user, profile, navigate, ask, transfer }: HomeProps) {
  // Hidden by default, as in banking apps: shoulder-surfing protection until the customer asks.
  const visibilityKey = `novabank-balance-visible:${user.id}`;
  const [shown, setShown] = useState(() => {
    try { return localStorage.getItem(visibilityKey) === 'true'; } catch { return false; }
  });
  const [copied, setCopied] = useState(false);
  const account = profile?.accounts[0];
  const totalBalance = profile?.accounts.reduce((sum, item) => sum + item.balance_vnd, 0) ?? 0;

  function toggleBalance() {
    const next = !shown;
    setShown(next);
    try { localStorage.setItem(visibilityKey, String(next)); } catch { /* Storage may be disabled. */ }
  }

  const quick = [
    { label: 'Transfer', icon: ArrowLeftRight, run: transfer },
    { label: 'Receive via QR', icon: QrCode, run: () => navigate('qr') },
    { label: 'History', icon: ReceiptText, run: () => navigate('activity') },
  ];

  async function copyAccount() {
    if (!account) return;
    try {
      await navigator.clipboard.writeText(account.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard blocked: nothing to confirm */ }
  }

  return (
    <div className="page home">
      <header className="page-head">
        <p className="muted">{greeting()}</p>
        <h1 className="page-title">{profile?.name ?? user.name}</h1>
      </header>

      <div className="dash">
        <section className="account-card dash-account" aria-label="Payment account">
          <div className="account-top">
            <span>Payment account</span>
            {account ? (
              <button className="account-no" onClick={copyAccount} aria-label={`Copy account number ${account.id}`}>
                {account.id} {copied ? <Check size={14} /> : <Copy size={14} />}
                <span className="copied" aria-live="polite">{copied ? 'Copied' : ''}</span>
              </button>
            ) : <span className="skeleton skeleton-text" />}
          </div>
          <span className="balance-label">Total available balance · {profile?.accounts.length ?? 0} payment accounts</span>
          <div className="balance-row">
            {account ? (
              <strong className={`balance ${shown ? 'is-shown' : ''}`} key={String(shown)}>
                {shown ? vnd(totalBalance) : '•••••••• VND'}
              </strong>
            ) : <span className="skeleton skeleton-balance" />}
            <button className="eye-button" onClick={toggleBalance} disabled={!account}
              aria-label={shown ? 'Hide balance' : 'Show balance'} aria-pressed={shown}>
              {shown ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
          <div className="quick-actions">
            {quick.map(({ label, icon: Icon, run }) => (
              <button key={label} onClick={run}>
                <span className="quick-icon"><Icon size={20} aria-hidden="true" /></span>
                <span>{label}</span>
              </button>
            ))}
          </div>
        </section>

        <div className="dash-month"><Overview user={user} explore={() => navigate('explore')} revision={account?.balance_vnd ?? 0} /></div>

        <section className="card nova-panel dash-nova" aria-labelledby="nova-title">
          <button className="assistant-head" onClick={() => navigate('assistant')}>
            <span className="assistant-avatar" aria-hidden="true">N</span>
            <span><strong id="nova-title">Nova assistant</strong><small>Available 24/7</small></span>
            <ChevronRight size={18} aria-hidden="true" />
          </button>
          <button className="fake-input" onClick={() => navigate('assistant')}>Ask about your balance, a payment or bank policy…</button>
          <p className="muted small">Or get an instant answer about:</p>
          <ul className="topic-list">
            {TOPICS.map(({ label, icon: Icon, text }) => (
              <li key={label}>
                <button className="topic" onClick={() => ask(text)}>
                  <span className="row-icon"><Icon size={18} aria-hidden="true" /></span>
                  <span>{label}</span>
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="card dash-tx">
          <div className="card-head">
            <h2 className="card-title">Recent transactions</h2>
            <button className="link-button" onClick={() => navigate('activity')}>See all <ChevronRight size={15} aria-hidden="true" /></button>
          </div>
          <ul className="tx-list">
            {profile ? profile.transactions.slice(0, 5).map(t => (
              <li key={t.id}>
                <button className="tx" onClick={() => navigate('activity')}>
                  <span className={`tx-icon ${t.direction}`}>{t.direction === 'in' ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</span>
                  <span className="tx-main"><strong>{t.description}</strong><small>{t.date}</small></span>
                  <span className={`tx-amount ${t.direction}`}>{t.direction === 'in' ? '+' : '-'}{vnd(t.amount_vnd)}</span>
                </button>
              </li>
            )) : [0, 1, 2].map(i => <li key={i} className="skeleton skeleton-row" />)}
          </ul>
          {profile?.transactions.length === 0 && <p className="muted">No transactions yet.</p>}
        </section>

        <button className="banner banner-security dash-safety" onClick={() => ask('Is it safe to share my OTP?')}>
          <ShieldCheck size={26} aria-hidden="true" />
          <strong>NovaBank never asks for your OTP</strong>
          <span>Not by phone, SMS or chat. Learn how to spot scams.</span>
        </button>
      </div>
    </div>
  );
}
