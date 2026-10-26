import { History, ShieldCheck, SquarePen } from 'lucide-react';

import type { Health } from '../../types';

interface TopbarProps {
  title: string;
  health: Health | null;
  busy: boolean;
  openHistory: () => void;
  openLog: () => void;
  startConversation: () => void;
}

export function Topbar({ title, health, busy, openHistory, openLog, startConversation }: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-heading">
        <span className="assistant-avatar" aria-hidden="true">N</span>
        <span>
          <span className="topbar-title">{title}</span>
          <span className={`model-pill ${!health ? 'is-connecting' : ''}`} role="status">
            <span className="status-dot" aria-hidden="true" />
            {health ? 'Online' : 'Connecting'}
          </span>
        </span>
      </div>
      <div className="topbar-right">
        <button className="tool-button" onClick={openHistory} aria-label="Conversation history">
          <History size={18} aria-hidden="true" /><span>History</span>
        </button>
        <button className="tool-button" onClick={startConversation} disabled={busy} aria-label="New conversation">
          <SquarePen size={18} aria-hidden="true" /><span>New</span>
        </button>
        <button className="tool-button" onClick={openLog} aria-label="Security log">
          <ShieldCheck size={18} aria-hidden="true" /><span>Security</span>
        </button>
      </div>
    </header>
  );
}
