import { ArrowUpRight, KeyRound, ShieldCheck, Sparkles, UserCheck } from 'lucide-react';

import type { DemoUser } from '../../types';

import { suggestions } from './suggestions';

interface WelcomeProps {
  user: DemoUser | null;
  busy: boolean;
  pickSuggestion: (text: string) => void;
}

const PROMISES = [
  { icon: <KeyRound size={15} aria-hidden="true" />, text: 'Never asks for your OTP, PIN or password' },
  { icon: <UserCheck size={15} aria-hidden="true" />, text: 'Payments are drafts until you approve' },
  { icon: <ShieldCheck size={15} aria-hidden="true" />, text: 'Every action is permission-checked' },
];

export function Welcome({ user, busy, pickSuggestion }: WelcomeProps) {
  return (
    <div className="welcome">
      <section className="welcome-hero">
        <span className="assistant-avatar assistant-avatar-lg" aria-hidden="true"><Sparkles size={28} /></span>
        <div>
          <h1>Hi{user ? ` ${user.name.split(' ')[0]}` : ''}, how can I help?</h1>
          <p>Check balances and payments, make a VietQR code, prepare a transfer or ask any banking question.</p>
        </div>
      </section>
      <ul className="welcome-promises">
        {PROMISES.map(p => <li key={p.text}>{p.icon}<span>{p.text}</span></li>)}
      </ul>
      <h2 className="welcome-label">Try asking</h2>
      <div className="suggestion-list">
        {suggestions.map(s => (
          <button key={s.title} className={`suggestion tone-${s.tone}`} disabled={!user || busy} onClick={() => pickSuggestion(s.text)}>
            <span className="suggestion-icon">{s.icon}</span>
            <span className="suggestion-text"><strong>{s.title}</strong><small>{s.detail}</small><q>{s.text}</q></span>
            <ArrowUpRight className="suggestion-go" size={18} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}
