import { Bell, House, LogOut, MessageCircle, Compass, ReceiptText, UserRound, ShieldCheck, LifeBuoy, ScanLine } from 'lucide-react';

import type { DemoUser } from '../../types';
import { initials } from '../../format';
import { navigate } from '../../router';

export type Tab = 'home' | 'activity' | 'qr' | 'assistant' | 'profile' | 'notifications' | 'admin' | 'explore' | 'support';

// On phones customers get five tabs with QR raised in the centre; Explore and Alerts move into Home.
const ITEMS: { id: Tab; label: string; icon: typeof House; desktopOnly?: boolean; center?: boolean }[] = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'activity', label: 'Activity', icon: ReceiptText },
  { id: 'qr', label: 'QR', icon: ScanLine, center: true },
  { id: 'assistant', label: 'Assistant', icon: MessageCircle },
  { id: 'explore', label: 'Explore', icon: Compass, desktopOnly: true },
  { id: 'notifications', label: 'Alerts', icon: Bell, desktopOnly: true },
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
    // Staff Home has no bell, so Alerts stays in their phone tab bar.
    ...ITEMS.filter(item => item.id === 'notifications' || item.id === 'profile').map(item => ({ ...item, desktopOnly: false })),
  ];
  return (
    <nav className="app-nav" aria-label="Main">
      {/* '/' resolves to each role's start page: Home for customers, the console for staff. */}
      <button className="nav-brand" aria-label="NovaBank home" onClick={() => navigate('/')}>
        <span className="brand-mark" aria-hidden="true">N</span>
        <span className="brand-word">nova<span>bank</span></span>
      </button>
      <ul className="nav-items">
        {items.map(({ id, label, icon: Icon, desktopOnly, center }) => (
          <li key={id} className={desktopOnly ? 'nav-desktop-only' : center ? 'nav-center' : undefined}>
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
