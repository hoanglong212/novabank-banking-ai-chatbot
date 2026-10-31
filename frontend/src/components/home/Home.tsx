import { useState } from 'react';
import {
  ArrowDownLeft, ArrowLeftRight, ArrowUpRight, Check, ChevronRight, ClipboardList, Copy, CreditCard, Eye, EyeOff,
  MapPin, MessageCircle, Percent, QrCode, ReceiptText, ShieldCheck,
} from 'lucide-react';

import type { DemoUser, Profile } from '../../types';
import type { Tab } from '../app/NavBar';
import { greeting, initials, vnd } from '../../format';

interface HomeProps {
  user: DemoUser;
  profile: Profile | null;
  navigate: (tab: Tab) => void;
  ask: (text: string) => void;
  transfer: () => void;
}

export function Home({ user, profile, navigate, ask, transfer }: HomeProps) {
  // Hidden by default, as in banking apps: shoulder-surfing protection until the customer asks.
  const [shown, setShown] = useState(false);
  const [copied, setCopied] = useState(false);
  const account = profile?.accounts[0];

  const quick = [
    { label: 'Transfer', icon: ArrowLeftRight, run: transfer },
    { label: 'VietQR', icon: QrCode, run: () => navigate('qr') },
    { label: 'History', icon: ReceiptText, run: () => navigate('activity') },
    { label: 'Assistant', icon: MessageCircle, run: () => navigate('assistant') },
  ];
  const services = [
    { label: 'Card services', icon: CreditCard, run: () => ask('My card is blocked, what should I do?') },
    { label: 'Security tips', icon: ShieldCheck, run: () => ask('How do I protect myself from banking fraud?') },
    { label: 'Fees & limits', icon: Percent, run: () => ask('What are the transfer fees and limits?') },
    { label: 'Branches & hours', icon: MapPin, run: () => ask('What are your opening hours?') },
    { label: 'Transaction status', icon: ReceiptText, run: () => ask('Check transaction TX-1002') },
    { label: 'Support ticket', icon: ClipboardList, run: () => ask('Create a support ticket for my pending transaction') },
    { label: 'Receive money', icon: QrCode, run: () => navigate('qr') },
    { label: 'Ask Nova', icon: MessageCircle, run: () => navigate('assistant') },
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
      <header className="home-greeting">
        <span className="avatar" aria-hidden="true">{initials(user.name)}</span>
        <div>
          <p>{greeting()}</p>
          <h1>{user.name}</h1>
        </div>
      </header>

      <div className="home-grid">
        <div className="home-main">
          <section className="account-card" aria-label="Payment account">
            <div className="account-top">
              <span>Payment account</span>
              {account ? (
                <button className="account-no" onClick={copyAccount} aria-label={`Copy account number ${account.id}`}>
                  {account.id} {copied ? <Check size={14} /> : <Copy size={14} />}
                  <span className="copied" aria-live="polite">{copied ? 'Copied' : ''}</span>
                </button>
              ) : <span className="skeleton skeleton-text" />}
            </div>
            <span className="balance-label">Available balance</span>
            <div className="balance-row">
              {account ? (
                <strong className={`balance ${shown ? 'is-shown' : ''}`} key={String(shown)}>
                  {shown ? vnd(account.balance_vnd) : '•••••••• VND'}
                </strong>
              ) : <span className="skeleton skeleton-balance" />}
              <button className="eye-button" onClick={() => setShown(!shown)} disabled={!account}
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

          <section className="card">
            <h2 className="card-title">Services</h2>
            <div className="service-grid">
              {services.map(({ label, icon: Icon, run }) => (
                <button key={label} className="service" onClick={run}>
                  <span className="service-icon"><Icon size={22} aria-hidden="true" /></span>
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="card-head">
              <h2 className="card-title">Recent transactions</h2>
              <button className="link-button" onClick={() => navigate('activity')}>See all <ChevronRight size={15} aria-hidden="true" /></button>
            </div>
            <ul className="tx-list">
              {profile ? profile.transactions.slice(0, 4).map(t => (
                <li key={t.id}>
                  <button className="tx" onClick={() => navigate('activity')}>
                    <span className={`tx-icon ${t.direction}`}>{t.direction === 'in' ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</span>
                    <span className="tx-main"><strong>{t.description}</strong><small>{t.date}</small></span>
                    <span className={`tx-amount ${t.direction}`}>{t.direction === 'in' ? '+' : '-'}{vnd(t.amount_vnd)}</span>
                  </button>
                </li>
              )) : [0, 1, 2].map(i => <li key={i} className="skeleton skeleton-row" />)}
            </ul>
          </section>
        </div>

        <aside className="home-side">
          <button className="assistant-card" onClick={() => navigate('assistant')}>
            <span className="assistant-head">
              <span className="assistant-avatar" aria-hidden="true">N</span>
              <span><strong>Nova assistant</strong><small>Available 24/7</small></span>
            </span>
            <span className="fake-input">Ask about your balance, a payment or VietQR…</span>
          </button>
          <div className="banner-strip">
            <button className="banner banner-security" onClick={() => ask('Is it safe to share my OTP?')}>
              <ShieldCheck size={26} aria-hidden="true" />
              <strong>NovaBank never asks for your OTP</strong>
              <span>Not by phone, SMS or chat. Learn how to spot scams.</span>
            </button>
            <button className="banner banner-qr" onClick={() => navigate('qr')}>
              <QrCode size={26} aria-hidden="true" />
              <strong>Get paid with VietQR</strong>
              <span>Create a code any Vietnamese banking app can scan.</span>
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}
