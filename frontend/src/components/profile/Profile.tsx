import { EyeOff, KeyRound, LogOut, ShieldCheck, Wallet } from 'lucide-react';

import type { DemoUser, Profile as ProfileData } from '../../types';
import { initials } from '../../format';
import { SecurityCenter } from './SecurityCenter';
import { ProfileEditor } from './ProfileEditor';
import { NotificationPreferences } from './NotificationPreferences';

interface ProfileProps {
  user: DemoUser;
  profile: ProfileData | null;
  logout: () => void;
}

const SECURITY = [
  { icon: KeyRound, title: 'Session', text: 'Sign-ins require a verification code. Manage your sessions below.' },
  { icon: EyeOff, title: 'Privacy', text: 'Account numbers, phones, emails and names are hidden from the assistant.' },
  { icon: ShieldCheck, title: 'Permissions', text: 'Every assistant action is permission-checked and logged.' },
];

export function Profile({ user, profile, logout }: ProfileProps) {
  return (
    <div className="page narrow profile-page">
      <section className="profile-head">
        <span className="avatar avatar-lg" aria-hidden="true">{initials(user.name)}</span>
        <strong>{user.name}</strong>
        <span className="muted">@{user.id} · {user.role && user.role !== 'customer' ? user.role : 'Personal customer'}</span>
      </section>
      <div className="profile-columns">
      <div className="profile-col">
      <ProfileEditor user={user} logout={logout} />
      <NotificationPreferences user={user} />
      </div>
      <div className="profile-col">
      <h2 className="section-label">Accounts</h2>
      <ul className="card settings-list">
        {profile?.accounts.length === 0 && <li className="muted">No personal payment accounts for this role.</li>}
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
      </div>
      </div>
      <SecurityCenter user={user} />
      <button className="danger-button" onClick={logout}><LogOut size={18} aria-hidden="true" /> Sign out</button>
      <p className="muted small center">NovaBank is a fictional bank for a classroom demo.</p>
    </div>
  );
}
