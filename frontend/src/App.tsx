import { Sidebar } from './components/layout/Sidebar';
import { Topbar } from './components/layout/Topbar';
import { Welcome } from './components/chat/Welcome';
import { MessageThread } from './components/chat/MessageThread';
import { Composer } from './components/chat/Composer';
import { TestingInsights } from './components/insights/TestingInsights';
import { useBankingChat } from './hooks/useBankingChat';

export default function App() {
  const chat = useBankingChat();

  return (
    <div className="app-shell">
      <a className="skip-link" href="#message-input">Skip to message input</a>
      <Sidebar

        user={chat.user}
        busy={chat.busy}
        conversations={chat.conversations}

        active={chat.active}
        setActive={chat.setActive}

        sidebarOpen={chat.sidebarOpen}
        setSidebarOpen={chat.setSidebarOpen}

        startConversation={chat.startConversation}
        deleteConversation={chat.deleteConversation}
      />
      <main className="main-area">
        <Topbar

          title={chat.messages.length > 0 && chat.activeTitle ? chat.activeTitle : 'Nova Assistant'}

          user={chat.user}
          users={chat.users}
          health={chat.health}
          busy={chat.busy}

          sidebarOpen={chat.sidebarOpen}
          setSidebarOpen={chat.setSidebarOpen}

          policyPanelOpen={chat.policyPanelOpen}
          setPolicyPanelOpen={chat.setPolicyPanelOpen}

          changeUser={chat.changeUser}
        />
        <div className="workspace">
          <section className="chat-column" aria-label="Chat with NovaBank">
            <div className="messages-scroller" ref={chat.scrollerRef}>
              <div className="messages-inner">
                {chat.messages.length === 0 ? (
                  <Welcome user={chat.user} busy={chat.busy} pickSuggestion={chat.pickSuggestion} />
                ) : (
                  <MessageThread messages={chat.messages} busy={chat.busy} />
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
          {chat.policyPanelOpen && (
            <TestingInsights

              health={chat.health}
              events={chat.events}
              setPolicyPanelOpen={chat.setPolicyPanelOpen}

              policy={{
                user: chat.user, busy: chat.busy,
                toolName: chat.toolName, setToolName: chat.setToolName,
                accountId: chat.accountId, setAccountId: chat.setAccountId,
                policyResult: chat.policyResult, setPolicyResult: chat.setPolicyResult,
                runPolicyDryRun: chat.runPolicyDryRun,
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}
