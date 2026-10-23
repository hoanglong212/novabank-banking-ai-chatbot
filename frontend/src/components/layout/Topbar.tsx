import { Menu, UserRound, PanelRight } from 'lucide-react';

import type { DemoUser, Health } from '../../types';

interface TopbarProps {
  title: string;
  user: DemoUser | null;
  health: Health | null;
  busy: boolean;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  policyPanelOpen: boolean;
  setPolicyPanelOpen: (open: boolean) => void;
  logout: () => void;
}

export function Topbar({
  title,
  user,
  health,
  busy,
  sidebarOpen,
  setSidebarOpen,
  policyPanelOpen,
  setPolicyPanelOpen,
  logout,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          aria-label="Open navigation"
          aria-expanded={sidebarOpen}
          aria-controls="navigation"
          className="menu-button icon-button"
          onClick={() => setSidebarOpen(true)}>
          <Menu size={22} />
        </button>
        <span className="topbar-title">
          {title}
        </span>
      </div>
      <div className="topbar-right">
        <span className={`model-pill ${!health ? 'is-connecting' : ''}`} role="status">
          <span className="status-dot" aria-hidden="true" />
          {health ? (health.llm_provider === 'ollama' ? 'Local AI model' : 'Demo mode') : 'Connecting'}
        </span>
        <div className="user-select-wrap">
          <UserRound size={16} aria-hidden="true" />
          <span>{user?.name}</span>
          <button type="button" disabled={busy} onClick={logout}>Sign out</button>
        </div>
        <button
          className={`insights-toggle icon-button ${policyPanelOpen ? 'is-active' : ''}`}
          aria-label="Testing insights"
          title="Testing insights"
          aria-controls="policy-panel"
          aria-expanded={policyPanelOpen}
          onClick={() => setPolicyPanelOpen(!policyPanelOpen)}>
          <PanelRight size={20} />
        </button>
      </div>
    </header>
  );
}
