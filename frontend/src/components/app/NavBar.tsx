import { House, LogOut, MessageCircle, QrCode, ReceiptText, UserRound } from 'lucide-react';

import type { DemoUser } from '../../types';
import { initials } from '../../format';

export type Tab = 'home' | 'activity' | 'qr' | 'assistant' | 'profile';

const ITEMS: { id: Tab; label: string; icon: typeof House }[] = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'activity', label: 'Activity', icon: ReceiptText },
  { id: 'qr', label: 'VietQR', icon: QrCode },
  { id: 'assistant', label: 'Assistant', icon: MessageCircle },
  { id: 'profile', label: 'Profile', icon: UserRound },
];

interface NavBarProps {
  tab: Tab;
  setTab: (tab: Tab) => void;
  user: DemoUser;
  logout: () => void;
}

// One navigation: a top bar on desktop, a bottom tab bar with a raised QR button on phones.
export function NavBar({ tab, setTab, user, logout }: NavBarProps) {
  return (
    <nav className="app-nav" aria-label="Main">
      <div className="nav-brand">
        <span className="brand-mark" aria-hidden="true">N</span>
        <span className="brand-word">nova<span>bank</span></span>
      </div>
      <ul className="nav-items">
        {ITEMS.map(({ id, label, icon: Icon }) => (
          <li key={id} className={id === 'profile' ? 'nav-profile-item' : undefined}>
            <button
              className={`nav-item ${id === 'qr' ? 'nav-qr' : ''}`}
              aria-current={tab === id ? 'page' : undefined}
              onClick={() => setTab(id)}>
              <span className="nav-icon"><Icon size={id === 'qr' ? 24 : 20} aria-hidden="true" /></span>
              <span className="nav-label">{label}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="nav-user">
        <button className="nav-user-button" onClick={() => setTab('profile')} aria-label="Open profile">
          <span className="avatar" aria-hidden="true">{initials(user.name)}</span>
          <span className="nav-user-name">{user.name}</span>
        </button>
        <button className="icon-button" aria-label="Sign out" title="Sign out" onClick={logout}>
          <LogOut size={18} />
        </button>
      </div>
    </nav>
  );
}
