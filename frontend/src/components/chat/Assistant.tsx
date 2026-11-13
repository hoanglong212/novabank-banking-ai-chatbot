import { useEffect, useRef, useState } from 'react';
import { ShieldCheck } from 'lucide-react';

import type { useBankingChat } from '../../hooks/useBankingChat';
import { Topbar } from '../layout/Topbar';
import { ToolActivity } from '../insights/ToolActivity';
import { Sheet } from '../ui/Sheet';
import { Composer } from './Composer';
import { ConversationList } from './ConversationList';
import { MessageThread } from './MessageThread';
import { Welcome } from './Welcome';
import { AgentActivity } from './AgentActivity';

// One chat column; history and the security log open as drawers instead of permanent side panels.
export function Assistant({ chat, openTransfer }: { chat: ReturnType<typeof useBankingChat>; openTransfer: (draftId: string) => void }) {
  const [panel, setPanel] = useState<'history' | 'log' | null>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const hasMessages = useRef(false);
  hasMessages.current = chat.messages.length > 0;
  // Proposals and run details load after the messages; keep the latest reply in view unless the reader scrolled up.
  useEffect(() => {
    const scroller = chat.scrollerRef.current, inner = innerRef.current;
    if (!scroller || !inner) return;
    let pinned = true, last = 0;
    const onScroll = () => {
      pinned = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 80 || scroller.scrollTop > last;
      last = scroller.scrollTop;
    };
    const observer = new ResizeObserver(() => { if (pinned && hasMessages.current) scroller.scrollTop = scroller.scrollHeight; });
    scroller.addEventListener('scroll', onScroll, { passive: true });
    observer.observe(inner);
    return () => { observer.disconnect(); scroller.removeEventListener('scroll', onScroll); };
  }, [chat.scrollerRef]);

  return (
    <div className="assistant">
      <Topbar
        title={chat.messages.length > 0 && chat.activeTitle ? chat.activeTitle : 'Nova assistant'}
        health={chat.health}
        busy={chat.busy}
        openHistory={() => setPanel('history')}
        openLog={() => setPanel('log')}
        startConversation={chat.startConversation}
        safeguards={chat.health?.agent_mode === 'service' ? (chat.defenseProfile === 'defended' ? 'Defended' : 'Baseline') : undefined}
      />
      <section className="chat-column" aria-label="Chat with Nova">
        <div className="messages-scroller" ref={chat.scrollerRef}>
          <div className="messages-inner" ref={innerRef}>
            {chat.user.role && chat.user.role !== 'customer' && <p className="staff-note"><ShieldCheck size={16} aria-hidden="true" />{chat.user.role === 'admin' ? 'Admin assistant · reports, ticket replies, and account, customer and settings changes. Nothing runs until you approve it here.' : chat.user.role === 'support' ? 'Support assistant · reads tickets and drafts replies or status changes. Nothing is sent until you approve it here.' : 'Staff assistant · read-only reports within your role. No payment or account changes.'}</p>}
            {chat.messages.length === 0 && (!chat.user.role || chat.user.role === 'customer') ? (
              <Welcome user={chat.user} busy={chat.busy} pickSuggestion={chat.pickSuggestion} />
            ) : (
              <MessageThread messages={chat.messages} busy={chat.busy} openTransfer={openTransfer} />
            )}
            {chat.busy && chat.progress && <p role="status" className="muted small">{chat.progress}</p>}
            {chat.active && (!chat.user.role || chat.user.role === 'customer' || chat.user.role === 'admin' || chat.user.role === 'support') && <AgentActivity user={chat.user} conversationId={chat.active} revision={chat.messages.length} openTransfer={openTransfer} />}
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
          stopResponse={chat.stopResponse}
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
        {/* The server honours Baseline only for an admin in a lab environment; everyone else always runs Defended. */}
        {chat.health?.agent_mode === 'service' && chat.user.role === 'admin' && <section className="safeguard-panel">
          <h3>Assistant safeguards</h3>
          <div className="safeguard-switch" role="radiogroup" aria-label="Assistant safeguards">
            {([['defended', 'Defended', 'Input screening and output checks on'], ['baseline', 'Baseline', 'Model only; bank permissions still apply']] as const).map(([id, label, hint]) => (
              <button key={id} role="radio" aria-checked={chat.defenseProfile === id} disabled={chat.busy} onClick={() => chat.setDefenseProfile(id)}>
                <strong>{label}</strong><small>{hint}</small>
              </button>
            ))}
          </div>
        </section>}
        <p className="muted small sheet-intro">What Nova tried to do in this conversation, and whether the permission check allowed it.</p>
        <ToolActivity events={chat.events} />
      </Sheet>
    </div>
  );
}
