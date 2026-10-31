import type { ChatMessage } from '../../types';

import { formatTime, safeMessageParts } from './messageFormatting';

const draftId = (text: string) => text.match(/TRF-[0-9A-F]{8}/)?.[0];

interface MessageThreadProps {
  messages: ChatMessage[];
  busy: boolean;
  openTransfer: (draftId: string) => void;
}

export function MessageThread({
  messages,
  busy,
  openTransfer,
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
            {m.role === 'assistant' && draftId(m.content) && (
              // Nova can only draft; the customer reviews and confirms with the OTP outside the chat.
              <button className="secondary-button draft-button" onClick={() => openTransfer(draftId(m.content)!)}>Review &amp; confirm</button>
            )}
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
