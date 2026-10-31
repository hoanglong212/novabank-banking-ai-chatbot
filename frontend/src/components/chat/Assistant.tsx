import { useState } from 'react';

import type { useBankingChat } from '../../hooks/useBankingChat';
import { Topbar } from '../layout/Topbar';
import { ToolActivity } from '../insights/ToolActivity';
import { Sheet } from '../ui/Sheet';
import { Composer } from './Composer';
import { ConversationList } from './ConversationList';
import { MessageThread } from './MessageThread';
import { Welcome } from './Welcome';

// One chat column; history and the security log open as drawers instead of permanent side panels.
export function Assistant({ chat, openTransfer }: { chat: ReturnType<typeof useBankingChat>; openTransfer: (draftId: string) => void }) {
  const [panel, setPanel] = useState<'history' | 'log' | null>(null);

  return (
    <div className="assistant">
      <Topbar
        title={chat.messages.length > 0 && chat.activeTitle ? chat.activeTitle : 'Nova assistant'}
        health={chat.health}
        busy={chat.busy}
        openHistory={() => setPanel('history')}
        openLog={() => setPanel('log')}
        startConversation={chat.startConversation}
      />
      <section className="chat-column" aria-label="Chat with Nova">
        <div className="messages-scroller" ref={chat.scrollerRef}>
          <div className="messages-inner">
            {chat.messages.length === 0 ? (
              <Welcome user={chat.user} busy={chat.busy} pickSuggestion={chat.pickSuggestion} />
            ) : (
              <MessageThread messages={chat.messages} busy={chat.busy} openTransfer={openTransfer} />
            )}
            <div ref={chat.endRef} />
          </div>
        </div>
        <Composer
          user={chat.user}
          busy={chat.busy}
          draft={chat.draft}
          setDraft={chat.setDraft}
          error={chat.error}
          setError={chat.setError}
          hasMessages={chat.messages.length > 0}
          textareaRef={chat.textareaRef}
          sendMessage={chat.sendMessage}
          pickSuggestion={chat.pickSuggestion}
        />
      </section>

      <Sheet open={panel === 'history'} onClose={() => setPanel(null)} title="Conversations" side="right">
        <ConversationList
          busy={chat.busy}
          conversations={chat.conversations}
          active={chat.active}
          open={id => { chat.setActive(id); setPanel(null); }}
          startConversation={() => { chat.startConversation(); setPanel(null); }}
          deleteConversation={chat.deleteConversation}
        />
      </Sheet>
      <Sheet open={panel === 'log'} onClose={() => setPanel(null)} title="Security log" side="right">
        <p className="muted small sheet-intro">What Nova tried to do in this conversation, and whether the permission check allowed it.</p>
        <ToolActivity events={chat.events} />
      </Sheet>
    </div>
  );
}
