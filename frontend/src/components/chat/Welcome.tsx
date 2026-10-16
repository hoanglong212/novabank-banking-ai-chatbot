import { ArrowUpRight, LockKeyhole } from 'lucide-react';

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
    <div className="bento">
      <div className="tile tile-hero">
        <p className="hero-kicker">Nova Assistant</p>
        <h1>Hello{user ? `, ${user.name.split(' ').slice(-1)[0]}` : ''}.<span>What can we sort out for you today?</span>
        </h1>
        <ul className="hero-facts">
          <li>Every account action is permission-checked</li>
          <li>Simulated data only</li>
        </ul>
      </div>
      {suggestions.map(s => (
        <button
          key={s.title}
          className={`tile tile-action tone-${s.tone}`}
          disabled={!user || busy}
          onClick={() => pickSuggestion(s.text)}>
          <span className="tile-icon">
            {s.icon}
          </span>
          <span className="tile-go" aria-hidden="true">
            <ArrowUpRight size={18} strokeWidth={2.25} />
          </span>
          <span className="tile-body">
            <strong>
              {s.title}
            </strong>
            <span className="tile-detail">
              {s.detail}
            </span>
            <span className="tile-example">“{s.text}”</span>
          </span>
        </button>
      ))}
      <div className="tile tile-safety">
        <LockKeyhole size={20} aria-hidden="true" />
        <p>
          <strong>Demo data only.</strong> Never enter real banking information.</p>
      </div>
    </div>
  );
}
