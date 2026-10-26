import { ChevronRight } from 'lucide-react';

import type { DemoUser } from '../../types';

import { suggestions } from './suggestions';

interface WelcomeProps {
  user: DemoUser | null;
  busy: boolean;
  pickSuggestion: (text: string) => void;
}

export function Welcome({
  user,
  busy,
  pickSuggestion,
}: WelcomeProps) {
  return (
    <div className="welcome">
      <span className="assistant-avatar assistant-avatar-lg" aria-hidden="true">N</span>
      <h1>Hi{user ? ` ${user.name.split(' ')[0]}` : ''}, how can I help?</h1>
      <p className="muted">I can check your balance and transactions, create VietQR codes and answer banking questions.
        I will never ask for your OTP, PIN or password.</p>
      <div className="suggestion-list">
        {suggestions.map(s => (
          <button
            key={s.title}
            className="suggestion"
            disabled={!user || busy}
            onClick={() => pickSuggestion(s.text)}>
            <span className="row-icon">{s.icon}</span>
            <span className="tx-main"><strong>{s.title}</strong><small>“{s.text}”</small></span>
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}
