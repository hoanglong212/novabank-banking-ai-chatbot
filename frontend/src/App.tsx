import { Sidebar } from './components/layout/Sidebar';
import { Topbar } from './components/layout/Topbar';
import { Welcome } from './components/chat/Welcome';
import { MessageThread } from './components/chat/MessageThread';
import { Composer } from './components/chat/Composer';
import { TestingInsights } from './components/insights/TestingInsights';
import { useBankingChat } from './hooks/useBankingChat';
import { useEffect, useState } from 'react';
import { api } from './api';
import type { DemoUser, Session } from './types';
import './styles/login.css';
import { BankingPanel } from './components/BankingPanel';

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    api.session().then(value => { if (alive) setSession(value); })
      .catch(e => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    const expired = () => { setSession(null); setError('Your session ended. Please sign in again.'); };
    window.addEventListener('novabank-session-expired', expired);
    return () => { alive = false; window.removeEventListener('novabank-session-expired', expired); };
  }, []);
  async function logout() {
    setBusy(true);
    try { await api.logout(); setSession(null); setError(''); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  if (loading) return <main className="login-page"><p role="status">Checking your session…</p></main>;
  if (session) return <>
    {error && <div role="alert">{error}</div>}
    <BankingApp key={session.user.id} user={session.user} logout={logout} sessionBusy={busy} />
  </>;
  return <main className="login-page"><form className="login-card" onSubmit={async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true); setError('');
    try {
      const next = await api.login(String(values.get('username')), String(values.get('password')));
      form.reset(); setSession(next);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }}>
    <h1>NovaBank</h1><p>Sign in to your demo account.</p>
    <label>Username<input name="username" autoComplete="username" required maxLength={80} disabled={busy} /></label>
    <label>Password<input name="password" type="password" autoComplete="current-password" required maxLength={256} disabled={busy} /></label>
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    <p>Simulated banking. Use the account provided by your demo administrator.</p>
  </form></main>;
}

function BankingApp({ user, logout, sessionBusy }: { user: DemoUser; logout: () => void; sessionBusy: boolean }) {
  const chat = useBankingChat(user);
  const [section,setSection] = useState<'chat' | 'banking'>(() =>
    window.sessionStorage.getItem('novabank-section-'+user.id)==='banking' ? 'banking' : 'chat');

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
          health={chat.health}
          busy={chat.busy || sessionBusy}

          sidebarOpen={chat.sidebarOpen}
          setSidebarOpen={chat.setSidebarOpen}

          policyPanelOpen={chat.policyPanelOpen}
          setPolicyPanelOpen={chat.setPolicyPanelOpen}

          logout={logout}
        />
        <nav className="workspace-tabs" aria-label="Application sections">
          {(['chat','banking'] as const).map(value => <button key={value} aria-pressed={section===value}
            onClick={() => {setSection(value); window.sessionStorage.setItem('novabank-section-'+user.id,value);}}>
            {value==='chat' ? 'Chat' : 'Accounts & transfers'}
          </button>)}
        </nav>
        <div className="workspace">
          {section==='banking' ? <BankingPanel user={user} /> : <>
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
          </>}
        </div>
      </main>
    </div>
  );
}
