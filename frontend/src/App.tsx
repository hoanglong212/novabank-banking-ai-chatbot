import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowRight, Bot, CheckCheck, ChevronDown, CircleHelp, ClipboardList, Clock3,
  CreditCard, Database, Landmark, LockKeyhole, Menu, MessageCircle,
  MessageSquare, Plus, Send, Shield, ShieldAlert, ShieldCheck, Trash2, UserRound,
  Wallet, Wrench, X, Sparkles, ArrowUpRight, PanelRight,
} from 'lucide-react';
import { api } from './api';
import type { ChatMessage, Conversation, DemoUser, Health, ToolEvent, Decision } from './types';

const suggestions = [
  { icon: <Wallet size={23} />, tone: 'mint', title: 'Check balance', detail: 'View your demo account balance.', text: 'Check my account balance' },
  { icon: <CreditCard size={23} />, tone: 'blue', title: 'Track a transaction', detail: 'Check your transaction status.', text: 'Check transaction TX-1002' },
  { icon: <CircleHelp size={23} />, tone: 'violet', title: 'Banking questions', detail: 'Explore VietQR and banking services.', text: 'What is VietQR and what should I check before scanning a code?' },
  { icon: <ClipboardList size={23} />, tone: 'amber', title: 'Get support', detail: 'Create a ticket for your issue.', text: 'Create a support ticket for my pending transaction' },
];

function formatTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return '';
  return parsed.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function safeMessageParts(text: string) {
  // Minimal formatting; messages are rendered as text, NOT unsanitized model HTML.
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, idx) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={idx}>{part.slice(2, -2)}</strong> : <span key={idx}>{part}</span>,
  );
}

function getInitials(name: string) { return name.trim().split(/\s+/).slice(-2).map(x => x[0]).join('').toUpperCase(); }

export default function App() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [user, setUser] = useState<DemoUser | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selection, setSelection] = useState<{ id: string; ownerId: string } | null>(null);
  const active = selection?.ownerId === user?.id ? selection?.id ?? null : null;
  const setActive = useCallback((id: string | null) => {
    setSelection(id && user ? { id, ownerId: user.id } : null);
  }, [user]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events, setEvents] = useState<ToolEvent[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [policyPanelOpen, setPolicyPanelOpen] = useState(false);
  const [toolName, setToolName] = useState('get_account_balance');
  const [accountId, setAccountId] = useState('ACC-BOB-001');
  const [policyResult, setPolicyResult] = useState<Decision | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.demoUsers(), api.health()]).then(([list, status]) => {
      if (!alive) return;
      setUsers(list);
      const remembered = list.find(item => item.id === window.sessionStorage.getItem('novabank-demo-user'));
      setUser(remembered || list[0] || null);
      setHealth(status);
    }).catch(err => { if (alive) setError(err.message + ' · Unable to connect to the support server.'); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!user) return;
    window.sessionStorage.setItem('novabank-demo-user', user.id);
    let cancelled = false;
    setActive(null); setMessages([]); setEvents([]); setError(null); setConversations([]);
    setDraft(''); setPolicyResult(null);
    api.listConversations(user).then(list => {
      if (cancelled) return;
      setConversations(list);
      if (list[0]) setActive(list[0].id);
    }).catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [user, setActive]);

  useEffect(() => {
    if (!user || !active) { setMessages([]); setEvents([]); return; }
    let cancelled = false;
    Promise.all([api.messages(user, active), api.toolEvents(user, active)]).then(([chat, log]) => {
      if (cancelled) return;
      setMessages(chat); setEvents(log);
    }).catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [user, active]);

  function changeUser(next: DemoUser) {
    if (busy || next.id === user?.id) return;
    setSelection(null); setMessages([]); setEvents([]); setConversations([]);
    setDraft(''); setPolicyResult(null); setError(null);
    setUser(next);
  }

  useEffect(() => {
    if (messages.length === 0 && !busy) {
      scrollerRef.current?.scrollTo({ top: 0 });
      return;
    }
    endRef.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [messages, busy]);

  useEffect(() => {
    function closePanels(event: KeyboardEvent) {
      if (event.key === 'Escape') { setSidebarOpen(false); setPolicyPanelOpen(false); }
    }
    window.addEventListener('keydown', closePanels);
    return () => window.removeEventListener('keydown', closePanels);
  }, []);

  const refreshConversations = useCallback(async (who: DemoUser) => setConversations(await api.listConversations(who)), []);

  async function startConversation() {
    if (!user || busy) return;
    setError(null); setBusy(true);
    try {
      const created = await api.createConversation(user, 'New conversation');
      await refreshConversations(user);
      setActive(created.id);
      setSidebarOpen(false);
      textareaRef.current?.focus();
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function deleteConversation(id: string) {
    if (!user || busy || !window.confirm('Delete this demo conversation?')) return;
    setBusy(true);
    try {
      await api.deleteConversation(user, id);
      const fresh = await api.listConversations(user);
      setConversations(fresh);
      if (active === id) setActive(fresh[0]?.id ?? null);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function sendMessage(value = draft) {
    if (!user || busy || !value.trim()) return;
    const content = value.trim();
    setBusy(true); setDraft(''); setError(null);
    try {
      let id = active;
      if (!id) {
        const created = await api.createConversation(user, content.slice(0, 55));
        id = created.id;
        setActive(created.id);
      }
      // Render local user intent promptly; authoritative history is reloaded after completion.
      setMessages(previous => [...previous, {
        id: 'pending-' + Date.now(), conversation_id: id!, role: 'user', content, created_at: new Date().toISOString(),
      }]);
      const response = await api.sendMessage(user, id, content);
      const [chat, log] = await Promise.all([api.messages(user, id), api.toolEvents(user, id)]);
      setMessages(chat); setEvents(log); await refreshConversations(user);
      if (response.message.role !== 'assistant') throw new Error('Unexpected backend response');
    } catch (err) {
      setError((err as Error).message + ' · Your message may have been saved. Check the conversation before sending it again.');
      if (active) api.messages(user, active).then(setMessages).catch(() => {});
    } finally { setBusy(false); }
  }

  async function runPolicyDryRun() {
    if (!user || busy) return;
    setPolicyResult(null); setError(null); setBusy(true);
    try {
      let id = active;
      if (!id) { const created = await api.createConversation(user, 'Policy test'); id = created.id; setActive(id); }
      const args: Record<string, unknown> = toolName === 'get_account_balance'
        ? { account_id: accountId.trim() || undefined }
        : toolName === 'get_transaction_status'
          ? { transaction_id: 'TX-2001' }
          : { query: 'What is VietQR?' };
      const response = await api.policyDryRun(user, id, toolName, args);
      setPolicyResult(response);
      setEvents(await api.toolEvents(user, id));
      await refreshConversations(user);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  const activeTitle = conversations.find(conversation => conversation.id === active)?.title;

  return (
    <div className="app-shell">
      <a className="skip-link" href="#message-input">Skip to message input</a>
      {sidebarOpen && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} id="navigation">
        <div className="brand">
          <span className="brand-symbol"><Landmark size={24} strokeWidth={1.8} /></span>
          <div><div className="brand-name">novabank<span>.</span></div><div className="brand-subtitle">BANKING, CLOSER TO YOU</div></div>
          <button className="mobile-close icon-button" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}><X size={20}/></button>
        </div>

        <div className="sidebar-section-label">YOUR WORKSPACE</div>
        <div className="nav-current"><MessageCircle size={19}/><span>Banking assistant</span><span className="nav-badge">AI</span></div>
        <button className="new-chat" onClick={startConversation} disabled={!user || busy}><Plus size={19}/><span>New conversation</span></button>

        <div className="sidebar-title"><Clock3 size={15}/><span>Recent</span><span className="count-badge">{conversations.length}</span></div>
        <nav className="conversation-list" aria-label="Conversation history">
          {conversations.length === 0 && <div className="no-chats"><MessageSquare size={22}/><p>Start a conversation.</p><span>Your conversations will appear here.</span></div>}
          {conversations.map(c => (
            <div key={c.id} className={`conversation ${c.id === active ? 'selected' : ''}`}>
              <button className="conversation-open" disabled={busy} aria-current={c.id === active ? 'page' : undefined} onClick={() => { setActive(c.id); setSidebarOpen(false); }} title={c.title}><MessageSquare size={16}/><span>{c.title}</span></button>
              <button className="conversation-remove icon-button" disabled={busy} title="Delete conversation" aria-label={`Delete conversation ${c.title}`} onClick={() => deleteConversation(c.id)}><Trash2 size={15}/></button>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-note"><span className="note-icon"><ShieldCheck size={20}/></span><strong>Explore with confidence</strong><p>Use demo data only.<br/>Never share your OTP or PIN.</p><span className="demo-tag">DEMO EDITION</span></div>
          <div className="profile-box"><div className="avatar">{user ? getInitials(user.name) : '—'}</div><div className="profile-details"><span className="profile-name">{user?.name ?? 'Connecting…'}</span><span className="profile-role">Demo account</span></div><span className="profile-dot"/></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button aria-label="Open navigation" aria-expanded={sidebarOpen} aria-controls="navigation" className="menu-button icon-button" onClick={() => setSidebarOpen(true)}><Menu size={22}/></button>
            <span className="breadcrumb">Support workspace</span><span className="breadcrumb-divider">/</span><span className="topbar-title">AI assistant</span>
          </div>
          <div className="topbar-right">
            <span className="model-pill"><span className="status-dot"/>{health ? (health.llm_provider === 'ollama' ? 'Ollama AI' : 'Demo mode') : 'Connecting'}</span>
            <label className="user-select-wrap"><UserRound size={16}/><select disabled={busy || !users.length} aria-label="Select demo customer" value={user?.id || ''} onChange={e => { const next = users.find(u => u.id === e.target.value); if (next) changeUser(next); }}>{users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select><ChevronDown size={14}/></label>
            <button className={`insights-toggle icon-button ${policyPanelOpen ? 'is-active' : ''}`} aria-label="Testing insights" title="Testing insights" aria-controls="policy-panel" aria-expanded={policyPanelOpen} onClick={() => setPolicyPanelOpen(!policyPanelOpen)}><PanelRight size={20}/></button>
          </div>
        </header>

        <div className="workspace">
          <section className="chat-column" aria-label="Chat with NovaBank">
            <div className="chat-heading"><div className="assistant-identity"><span className="assistant-symbol"><Sparkles size={20}/></span><div><strong>Nova Assistant</strong><span>Your banking assistant</span></div></div><span className="chat-context">{messages.length > 0 ? activeTitle : 'Here whenever you need us'}</span></div>
            <div className="messages-scroller" ref={scrollerRef}><div className="messages-inner">
              {messages.length === 0 ? (
                <div className="welcome">
                  <div className="welcome-topline"><span className="welcome-kicker"><span className="tiny-spark"><Sparkles size={14}/></span> A NEW WAY TO CONNECT</span><span className="welcome-edition">NOVABANK / AI</span></div>
                  <div className="welcome-heading"><h1>Hello{user ? `, ${user.name.split(' ').slice(-1)[0]}` : ''}.<br/><span>How can we help today?</span></h1><div className="welcome-mark" aria-hidden="true"><Landmark size={36} strokeWidth={1.4}/><span><Sparkles size={14}/></span></div></div>
                  <p className="welcome-description">From a quick question to a helping hand.<br className="desktop-break"/> Nova is here to help you find answers.</p>
                  <div className="section-caption"><span>LET'S GET STARTED</span><span>Choose a suggestion below <ArrowRight size={14}/></span></div>
                  <div className="suggestions">
                    {suggestions.map((s, index) => (
                      <button key={s.title} className={`suggestion-card tone-${s.tone}`} disabled={!user || busy} onClick={() => { setDraft(s.text); textareaRef.current?.focus(); }}>
                        <div className="suggestion-top"><span className="suggestion-icon">{s.icon}</span><span className="suggestion-number">0{index + 1}</span></div>
                        <strong>{s.title}</strong><span className="suggestion-detail">{s.detail}</span><ArrowUpRight size={19} className="suggestion-arrow"/>
                      </button>
                    ))}
                  </div>
                  <div className="welcome-footnote"><LockKeyhole size={15}/><span>Use demo data only. Never enter real banking information.</span></div>
                </div>
              ) : (
                <div className="chat-thread" role="log" aria-label="Conversation messages" aria-live="polite">
                  <div className="thread-start"><span/>Conversation started<span/></div>
                  {messages.map(m => (
                    <div className={`message-row ${m.role === 'user' ? 'message-user' : 'message-assistant'}`} key={m.id}>
                      {m.role === 'assistant' && <div className="bot-icon"><Sparkles size={18}/></div>}
                      <div className="message-body"><div className="message-author">{m.role === 'assistant' ? 'Nova Assistant' : 'You'}<span>{formatTime(m.created_at)}</span></div><div className="message-content">{safeMessageParts(m.content)}</div></div>
                      {m.role === 'user' && <div className="me-icon">{user ? getInitials(user.name) : 'U'}</div>}
                    </div>
                  ))}
                  {busy && <div className="message-row message-assistant"><div className="bot-icon"><Bot size={18}/></div><div className="typing" role="status" aria-label="Nova is typing"><span/><span/><span/><small>Nova is typing</small></div></div>}
                </div>
              )}
              <div ref={endRef}/>
            </div></div>

            <div className="composer-area">
              {error && <div className="error-banner" role="alert"><ShieldAlert size={18}/><span>{error}</span><button className="icon-button" aria-label="Dismiss notification" onClick={() => setError(null)}><X size={17}/></button></div>}
              <div className="composer"><span className="composer-spark"><Sparkles size={20}/></span><textarea id="message-input" ref={textareaRef} rows={1} placeholder="What would you like to know?" value={draft} disabled={!user || busy} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void sendMessage(); } }} aria-label="Message"/><button className="send-button" aria-label="Send message" disabled={!draft.trim() || busy || !user} onClick={() => void sendMessage()}><Send size={19}/></button></div>
              <div className="composer-foot"><span><Shield size={13}/> NovaBank AI · Simulated data</span><span><kbd>Enter</kbd> to send <span className="foot-divider">·</span> <kbd>Shift + Enter</kbd> for a new line</span></div>
            </div>
          </section>

          {policyPanelOpen && <>
            <button className="inspector-overlay" aria-label="Close testing insights" onClick={() => setPolicyPanelOpen(false)}/>
            <aside className="inspector" id="policy-panel" aria-label="Testing insights">
              <div className="inspector-header"><div><ShieldCheck size={20}/><strong>Testing insights</strong></div><button className="icon-button" aria-label="Close testing insights" onClick={() => setPolicyPanelOpen(false)}><X size={19}/></button></div>
              <div className="inspector-content">
                <div className="inspector-card"><div className="card-kicker"><span className="status-dot"/> ACCESS CONTROL</div><h3>Demo policy layer</h3><p>Permissions are checked before tools run. The team's live gateway is not connected yet.</p><div className="stats-row"><div><span>Gateway</span><strong>{health?.gateway_mode ?? '—'}</strong></div><div><span>Model</span><strong>{health?.llm_provider ?? '—'}</strong></div></div></div>
                <div className="panel-section-heading"><Wrench size={16}/> Tool activity <span>{events.length}</span></div>
                <div className="activity-list">{events.length === 0 ? <div className="empty-activity"><Database size={25}/><p>No activity yet</p><small>Tool checks will appear here.</small></div> : events.slice(-6).reverse().map(e => <div className="event" key={e.id}><span className={`event-dot ${e.decision === 'ALLOW' ? 'allowed' : 'denied'}`}/><div className="event-content"><strong title={e.tool_name}>{e.tool_name}</strong><span>{e.reason_code.replace(/_/g, ' ')}</span></div><span className={`event-label ${e.decision === 'ALLOW' ? 'allowed' : 'denied'}`}>{e.decision}</span></div>)}</div>
                <div className="panel-section-heading"><Shield size={16}/> Check permissions <span className="dryrun-label">DRY RUN</span></div>
                <div className="policy-test"><p>Checks permissions without executing the tool.</p><label>Tool<select value={toolName} onChange={e => { setToolName(e.target.value); setPolicyResult(null); }}><option value="get_account_balance">Check balance</option><option value="get_transaction_status">Track a transaction</option><option value="search_banking_faq">Search FAQs</option></select></label>{toolName === 'get_account_balance' && <label>Account ID<input value={accountId} onChange={e => { setAccountId(e.target.value); setPolicyResult(null); }} placeholder="ACC-ALICE-001"/></label>}{toolName === 'get_transaction_status' && <div className="test-note">Demo transaction TX-2001 belongs to Bob.</div>}<button className="test-button" onClick={runPolicyDryRun} disabled={!user || busy}>Check permissions <ArrowRight size={16}/></button>{policyResult && <div role="status" className={`policy-result ${policyResult.decision.toLowerCase()}`}>{policyResult.decision === 'ALLOW' ? <CheckCheck size={17}/> : <ShieldAlert size={17}/>}<span>{policyResult.decision} · {policyResult.reason_code}</span></div>}</div>
                <div className="inspector-info"><CircleHelp size={17}/><p>Architecture demonstration only. This is not a banking security certification.</p></div>
              </div>
            </aside>
          </>}
        </div>
      </main>
    </div>
  );
}
