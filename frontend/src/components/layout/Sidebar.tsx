import { Landmark, X, Plus, MessageSquare, Trash2, ShieldCheck } from 'lucide-react';

import type { Conversation, DemoUser } from '../../types';

interface SidebarProps {
  user: DemoUser | null;
  busy: boolean;
  conversations: Conversation[];
  active: string | null;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  setActive: (id: string | null) => void;
  startConversation: () => void;
  deleteConversation: (id: string) => void;
}

function getInitials(name: string) {
  return name.trim().split(/\s+/).slice(-2).map(x => x[0]).join('').toUpperCase();
}

export function Sidebar({
  user,
  busy,
  conversations,
  active,
  sidebarOpen,
  setSidebarOpen,
  setActive,
  startConversation,
  deleteConversation,
}: SidebarProps) {
  return (
    <>
      {sidebarOpen && <button
        className="mobile-overlay"
        aria-label="Close navigation"
        onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} id="navigation">
        <div className="brand">
          <span className="brand-symbol" aria-hidden="true">
            <Landmark size={20} strokeWidth={2} />
          </span>
          <div className="brand-name">nova<span>bank</span>
          </div>
          <button
            className="mobile-close icon-button"
            aria-label="Close navigation"
            onClick={() => setSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <button className="new-chat" onClick={startConversation} disabled={!user || busy}>
          <Plus size={18} strokeWidth={2.5} aria-hidden="true" />
          <span>New conversation</span>
        </button>

        <div className="sidebar-title">
          <span>Your conversations</span>
          <span className="count-badge">
            {conversations.length}
          </span>
        </div>
        <nav className="conversation-list" aria-label="Conversation history">
          {conversations.length === 0 && <div className="no-chats">
            <p>Nothing here yet</p>
            <span>Start a conversation and it will show up here.</span>
          </div>}
          {conversations.map(c => (
            <div key={c.id} className={`conversation ${c.id === active ? 'selected' : ''}`}>
              <button
                className="conversation-open"
                disabled={busy}
                aria-current={c.id === active ? 'page' : undefined}
                onClick={() => {
                  setActive(c.id);
                  setSidebarOpen(false);
                }}
                title={c.title}>
                <MessageSquare size={16} aria-hidden="true" />
                <span>
                  {c.title}
                </span>
              </button>
              <button
                className="conversation-remove icon-button"
                disabled={busy}
                title="Delete conversation"
                aria-label={`Delete conversation ${c.title}`}
                onClick={() => deleteConversation(c.id)}>
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-note">
            <ShieldCheck size={20} aria-hidden="true" />
            <p>
              <strong>Demo edition</strong>Never share your OTP or PIN, not even with Nova.</p>
          </div>
          <div className="profile-box">
            <div className="avatar" aria-hidden="true">
              {user ? getInitials(user.name) : '—'}
            </div>
            <div className="profile-details">
              <span className="profile-name">
                {user?.name ?? 'Connecting…'}
              </span>
              <span className="profile-role">Demo customer</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
