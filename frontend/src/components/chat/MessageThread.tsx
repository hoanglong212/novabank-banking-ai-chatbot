import type { ChatMessage } from '../../types';

import { formatTime, safeMessageParts } from './messageFormatting';

interface MessageThreadProps {
  messages: ChatMessage[];
  busy: boolean;
}

export function MessageThread({
  messages,
  busy,
}: MessageThreadProps) {
  return (
    <div className="chat-thread" role="log" aria-label="Conversation messages" aria-live="polite">
      {messages.map(m => (
        <div
          className={`message-row ${m.role === 'user' ? 'message-user' : 'message-assistant'}`}
          key={m.id}>
          {m.role === 'assistant' && <div className="bot-icon" aria-hidden="true">N</div>}
          <div className="message-body">
            <div className="message-author">
              {m.role === 'assistant' ? 'Nova' : 'You'}
              <span>
                {formatTime(m.created_at)}
              </span>
            </div>
            <div className="message-content">
              {safeMessageParts(m.content)}
            </div>
          </div>
        </div>
      ))}
      {busy && <div className="message-row message-assistant">
        <div className="bot-icon" aria-hidden="true">N</div>
        <div className="typing" role="status" aria-label="Nova is typing">
          <span />
          <span />
          <span />
          <small>Nova is on it</small>
        </div>
      </div>}
    </div>
  );
}
