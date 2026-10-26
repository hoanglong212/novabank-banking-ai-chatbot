import { MessageSquare, Plus, Trash2 } from 'lucide-react';

import type { Conversation } from '../../types';

interface ConversationListProps {
  busy: boolean;
  conversations: Conversation[];
  active: string | null;
  open: (id: string) => void;
  startConversation: () => void;
  deleteConversation: (id: string) => void;
}

export function ConversationList({ busy, conversations, active, open, startConversation, deleteConversation }: ConversationListProps) {
  return (
    <div className="conversation-panel">
      <button className="new-chat" onClick={startConversation} disabled={busy}>
        <Plus size={18} strokeWidth={2.5} aria-hidden="true" /> New conversation
      </button>
      <nav className="conversation-list" aria-label="Conversation history">
        {conversations.length === 0 && <p className="muted small">No conversations yet.</p>}
        {conversations.map(c => (
          <div key={c.id} className={`conversation ${c.id === active ? 'selected' : ''}`}>
            <button
              className="conversation-open"
              disabled={busy}
              aria-current={c.id === active ? 'page' : undefined}
              onClick={() => open(c.id)}
              title={c.title}>
              <MessageSquare size={16} aria-hidden="true" />
              <span>{c.title}</span>
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
    </div>
  );
}
