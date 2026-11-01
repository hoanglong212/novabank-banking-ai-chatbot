import type { ReactNode } from 'react';
import { MessageCircle, QrCode, ShieldCheck } from 'lucide-react';

export function AuthShell({ children }: { children: ReactNode }) {
  return <div className="login-page">
    <section className="login-hero" aria-hidden="true">
      <div className="nav-brand">
        <span className="brand-mark">N</span>
        <span className="brand-word">nova<span>bank</span></span>
      </div>
      <h2>Your money, with an assistant that never sleeps.</h2>
      <ul>
        <li><MessageCircle size={18} /> Ask Nova about balances, payments and banking questions</li>
        <li><QrCode size={18} /> Create VietQR payment codes in seconds</li>
        <li><ShieldCheck size={18} /> Every AI action is permission-checked; personal data stays hidden from the AI</li>
      </ul>
    </section>
    <main className="login-panel">
      {children}
      <p className="login-foot">Fictional bank for a classroom demo. Never use real banking credentials.</p>
    </main>
  </div>;
}
