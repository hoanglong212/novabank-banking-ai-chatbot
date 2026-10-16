import type { RefObject } from 'react';

import { ShieldAlert, X, Send, Shield } from 'lucide-react';

import type { DemoUser } from '../../types';

import { suggestions } from './suggestions';

interface ComposerProps {
  user: DemoUser | null;
  busy: boolean;
  draft: string;
  setDraft: (draft: string) => void;
  error: string | null;
  setError: (error: string | null) => void;
  hasMessages: boolean;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  sendMessage: () => void;
  pickSuggestion: (text: string) => void;
}

export function Composer({
  user,
  busy,
  draft,
  setDraft,
  error,
  setError,
  hasMessages,
  textareaRef,
  sendMessage,
  pickSuggestion,
}: ComposerProps) {
  return (
    <div className="composer-area">
      {error && <div className="error-banner" role="alert">
        <ShieldAlert size={18} aria-hidden="true" />
        <span>
          {error}
        </span>
        <button className="icon-button" aria-label="Dismiss notification" onClick={() => setError(null)}>
          <X size={17} />
        </button>
      </div>}
      {hasMessages && <div className="quick-chips" aria-label="Quick requests">
        {suggestions.map(s => <button
          key={s.chip}
          className={`chip tone-${s.tone}`}
          disabled={!user || busy}
          onClick={() => pickSuggestion(s.text)}>
          {s.icon}
          <span>
            {s.chip}
          </span>
        </button>)}
      </div>}
      <div className="composer">
        <textarea
          id="message-input"
          ref={textareaRef}
          rows={1}
          placeholder="Ask Nova anything about your money"
          value={draft}
          disabled={!user || busy}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              void sendMessage();
            }
          }}
          aria-label="Message" />
        <button
          className="send-button"
          aria-label="Send message"
          disabled={!draft.trim() || busy || !user}
          onClick={() => void sendMessage()}>
          <Send size={18} strokeWidth={2.25} />
        </button>
      </div>
      <div className="composer-foot">
        <span>
          <Shield size={13} aria-hidden="true" /> Simulated data · Nova can make mistakes</span>
        <span>
          <kbd>Enter</kbd> send · <kbd>Shift</kbd>+<kbd>Enter</kbd> new line</span>
      </div>
    </div>
  );
}
