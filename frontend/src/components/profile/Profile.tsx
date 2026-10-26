import { EyeOff, KeyRound, LogOut, ShieldCheck, Wallet } from 'lucide-react';

import type { DemoUser, Profile as ProfileData } from '../../types';
import { initials } from '../../format';

interface ProfileProps {
  user: DemoUser;
  profile: ProfileData | null;
  logout: () => void;
}

const SECURITY = [
  { icon: KeyRound, title: 'Session', text: 'Signed in with a token that expires after 60 minutes. Closing the tab signs you out.' },
  { icon: EyeOff, title: 'Privacy', text: 'Account numbers, phones, emails and names are hidden from the assistant.' },
  { icon: ShieldCheck, title: 'Permissions', text: 'Every assistant action is permission-checked and logged.' },
];

export function Profile({ user, profile, logout }: ProfileProps) {
  return (
    <div className="page narrow">
      <section className="profile-head">
        <span className="avatar avatar-lg" aria-hidden="true">{initials(user.name)}</span>
        <strong>{user.name}</strong>
        <span className="muted">@{user.id} · Personal customer</span>
      </section>
      <h2 className="section-label">Accounts</h2>
      <ul className="card settings-list">
        {(profile?.accounts ?? []).map(a => (
          <li key={a.id}>
            <span className="row-icon"><Wallet size={20} aria-hidden="true" /></span>
            <span className="tx-main"><strong>Payment account</strong><small>{a.id} · {a.currency}</small></span>
          </li>
        ))}
      </ul>
      <h2 className="section-label">Security & privacy</h2>
      <ul className="card settings-list">
        {SECURITY.map(({ icon: Icon, title, text }) => (
          <li key={title}>
            <span className="row-icon"><Icon size={20} aria-hidden="true" /></span>
            <span className="tx-main"><strong>{title}</strong><small>{text}</small></span>
          </li>
        ))}
      </ul>
      <button className="danger-button" onClick={logout}><LogOut size={18} aria-hidden="true" /> Sign out</button>
      <p className="muted small center">NovaBank is a fictional bank for a classroom demo.</p>
    </div>
  );
}
