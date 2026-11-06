import { Bell, House, LogOut, MessageCircle, Compass, ReceiptText, UserRound, ShieldCheck, LifeBuoy } from 'lucide-react';

import type { DemoUser } from '../../types';
import { initials } from '../../format';

export type Tab = 'home' | 'activity' | 'qr' | 'assistant' | 'profile' | 'notifications' | 'admin' | 'explore' | 'support';

const ITEMS: { id: Tab; label: string; icon: typeof House }[] = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'activity', label: 'Activity', icon: ReceiptText },
  { id: 'assistant', label: 'Assistant', icon: MessageCircle },
  { id: 'explore', label: 'Explore', icon: Compass },
  { id: 'notifications', label: 'Alerts', icon: Bell },
  { id: 'profile', label: 'Profile', icon: UserRound },
];

interface NavBarProps {
  tab: Tab;
  setTab: (tab: Tab) => void;
  user: DemoUser;
  logout: () => void;
}

// One navigation: a left sidebar on desktop, a bottom tab bar on phones.
export function NavBar({ tab, setTab, user, logout }: NavBarProps) {
  const items = !user.role || user.role === 'customer' ? ITEMS : [
    { id: 'assistant' as const, label: 'Staff assistant', icon: MessageCircle },
    ...(user.permissions?.includes('admin:transactions:read') ? [{ id: 'admin' as const, label: 'Operations', icon: ShieldCheck }] : []),
    ...(user.permissions?.includes('support:read') ? [{ id: 'support' as const, label: 'Support', icon: LifeBuoy }] : []),
    ...ITEMS.filter(item => item.id === 'notifications' || item.id === 'profile'),
  ];
  return (
    <nav className="app-nav" aria-label="Main">
      <div className="nav-brand">
        <span className="brand-mark" aria-hidden="true">N</span>
        <span className="brand-word">nova<span>bank</span></span>
      </div>
      <ul className="nav-items">
        {items.map(({ id, label, icon: Icon }) => (
          <li key={id}>
            <button className="nav-item" data-tab={id} aria-label={label} aria-current={tab === id ? 'page' : undefined} onClick={() => setTab(id)}>
              <span className="nav-icon"><Icon size={20} aria-hidden="true" /></span>
              <span className="nav-label">{label}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="nav-user">
        <span className="avatar" aria-hidden="true">{initials(user.name)}</span>
        <span className="nav-user-name">{user.name}<small>@{user.id}</small></span>
        <button className="icon-button" aria-label="Sign out" title="Sign out" onClick={logout}>
          <LogOut size={18} />
        </button>
      </div>
    </nav>
  );
}
