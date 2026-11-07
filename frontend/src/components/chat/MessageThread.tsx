import { useState } from 'react';
import { Check, Copy, Sparkles } from 'lucide-react';

import type { ChatMessage } from '../../types';

import { formatTime, safeMessageParts } from './messageFormatting';

const draftId = (text: string) => text.match(/\bTRF-(?:[0-9A-F]{32}|[0-9A-F]{8})\b/)?.[0];
const dayKey = (iso: string) => new Date(iso).toLocaleDateString('sv-SE');

function dayName(iso: string) {
  const key = dayKey(iso);
  if (key === dayKey(new Date().toISOString())) return 'Today';
  if (key === dayKey(new Date(Date.now() - 86_400_000).toISOString())) return 'Yesterday';
  return new Date(iso).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text.replace(/!\[VietQR\]\([^)]*\)/g, '').replaceAll('**', '').trim());
      setDone(true);
      window.setTimeout(() => setDone(false), 1600);
    } catch { /* Clipboard may be blocked; nothing to undo. */ }
  }
  return <button className="message-action" onClick={() => void copy()} aria-label={done ? 'Copied' : 'Copy message'} title={done ? 'Copied' : 'Copy'}>
    {done ? <Check size={14} /> : <Copy size={14} />}<span>{done ? 'Copied' : 'Copy'}</span>
  </button>;
}

interface MessageThreadProps {
  messages: ChatMessage[];
  busy: boolean;
  openTransfer: (draftId: string) => void;
}

export function MessageThread({ messages, busy, openTransfer }: MessageThreadProps) {
  return (
    <div className="chat-thread" role="log" aria-label="Conversation messages" aria-live="polite">
      {messages.map((m, i) => {
        const newDay = !Number.isNaN(new Date(m.created_at).valueOf()) && (i === 0 || dayKey(messages[i - 1].created_at) !== dayKey(m.created_at));
        return <div key={m.id}>
          {newDay && <div className="chat-day"><span>{dayName(m.created_at)}</span></div>}
          <div className={`message-row ${m.role === 'user' ? 'message-user' : 'message-assistant'}`}>
            {m.role === 'assistant' && <div className="bot-icon" aria-hidden="true"><Sparkles size={15} /></div>}
            <div className="message-body">
              <div className="message-author">
                {m.role === 'assistant' ? 'Nova' : 'You'}
                <span>{formatTime(m.created_at)}</span>
              </div>
              <div className="message-content">{safeMessageParts(m.content)}</div>
              {m.role === 'assistant' && <div className="message-actions">
                {draftId(m.content) && (
                  // Nova can only draft; the customer reviews and confirms with the OTP outside the chat.
                  <button className="primary-button draft-button" onClick={() => openTransfer(draftId(m.content)!)}>Review &amp; confirm</button>
                )}
                <CopyButton text={m.content} />
              </div>}
            </div>
          </div>
        </div>;
      })}
      {busy && <div className="message-row message-assistant">
        <div className="bot-icon is-thinking" aria-hidden="true"><Sparkles size={15} /></div>
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
