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
  { icon: <Wallet size={23} />, tone: 'mint', title: 'Kiểm tra số dư', detail: 'Xem số dư tài khoản demo của bạn.', text: 'Kiểm tra số dư tài khoản của tôi' },
  { icon: <CreditCard size={23} />, tone: 'blue', title: 'Tra cứu giao dịch', detail: 'Theo dõi trạng thái chuyển tiền.', text: 'Kiểm tra trạng thái giao dịch TX-1002' },
  { icon: <CircleHelp size={23} />, tone: 'violet', title: 'Giải đáp ngân hàng', detail: 'Tìm hiểu VietQR và các dịch vụ.', text: 'VietQR là gì và tôi cần chú ý điều gì khi quét mã?' },
  { icon: <ClipboardList size={23} />, tone: 'amber', title: 'Yêu cầu hỗ trợ', detail: 'Tạo phiếu hỗ trợ cho vấn đề của bạn.', text: 'Tạo yêu cầu hỗ trợ vì giao dịch bị treo' },
];

function formatTime(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return '';
  return parsed.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
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
    }).catch(err => { if (alive) setError(err.message + ' · Chưa kết nối được máy chủ hỗ trợ.'); });
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
      const created = await api.createConversation(user, 'Cuộc trò chuyện mới');
      await refreshConversations(user);
      setActive(created.id);
      setSidebarOpen(false);
      textareaRef.current?.focus();
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function deleteConversation(id: string) {
    if (!user || busy || !window.confirm('Xóa cuộc trò chuyện demo này?')) return;
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
      setError((err as Error).message + ' · Nội dung đã gửi có thể vẫn được lưu. Kiểm tra history trước khi gửi lại.');
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
          : { query: 'VietQR là gì?' };
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
      <a className="skip-link" href="#message-input">Đến ô nhập tin nhắn</a>
      {sidebarOpen && <button className="mobile-overlay" aria-label="Đóng điều hướng" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} id="navigation">
        <div className="brand">
          <span className="brand-symbol"><Landmark size={24} strokeWidth={1.8} /></span>
          <div><div className="brand-name">novabank<span>.</span></div><div className="brand-subtitle">NGÂN HÀNG, GẦN BẠN HƠN</div></div>
          <button className="mobile-close icon-button" aria-label="Đóng điều hướng" onClick={() => setSidebarOpen(false)}><X size={20}/></button>
        </div>

        <div className="sidebar-section-label">KHÔNG GIAN CỦA BẠN</div>
        <div className="nav-current"><MessageCircle size={19}/><span>Trợ lý ngân hàng</span><span className="nav-badge">AI</span></div>
        <button className="new-chat" onClick={startConversation} disabled={!user || busy}><Plus size={19}/><span>Cuộc trò chuyện mới</span></button>

        <div className="sidebar-title"><Clock3 size={15}/><span>Gần đây</span><span className="count-badge">{conversations.length}</span></div>
        <nav className="conversation-list" aria-label="Lịch sử hội thoại">
          {conversations.length === 0 && <div className="no-chats"><MessageSquare size={22}/><p>Câu chuyện bắt đầu từ bạn.</p><span>Các cuộc trò chuyện sẽ được lưu ở đây.</span></div>}
          {conversations.map(c => (
            <div key={c.id} className={`conversation ${c.id === active ? 'selected' : ''}`}>
              <button className="conversation-open" disabled={busy} aria-current={c.id === active ? 'page' : undefined} onClick={() => { setActive(c.id); setSidebarOpen(false); }} title={c.title}><MessageSquare size={16}/><span>{c.title}</span></button>
              <button className="conversation-remove icon-button" disabled={busy} title="Xóa hội thoại" aria-label={`Xóa hội thoại ${c.title}`} onClick={() => deleteConversation(c.id)}><Trash2 size={15}/></button>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-note"><span className="note-icon"><ShieldCheck size={20}/></span><strong>Trải nghiệm an tâm</strong><p>Chỉ sử dụng dữ liệu giả lập.<br/>Không chia sẻ OTP hoặc mã PIN.</p><span className="demo-tag">PHIÊN BẢN DEMO</span></div>
          <div className="profile-box"><div className="avatar">{user ? getInitials(user.name) : '—'}</div><div className="profile-details"><span className="profile-name">{user?.name ?? 'Đang kết nối…'}</span><span className="profile-role">Tài khoản trải nghiệm</span></div><span className="profile-dot"/></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button aria-label="Mở điều hướng" aria-expanded={sidebarOpen} aria-controls="navigation" className="menu-button icon-button" onClick={() => setSidebarOpen(true)}><Menu size={22}/></button>
            <span className="breadcrumb">Không gian hỗ trợ</span><span className="breadcrumb-divider">/</span><span className="topbar-title">Trợ lý AI</span>
          </div>
          <div className="topbar-right">
            <span className="model-pill"><span className="status-dot"/>{health ? (health.llm_provider === 'ollama' ? 'Ollama AI' : 'Chế độ demo') : 'Đang kết nối'}</span>
            <label className="user-select-wrap"><UserRound size={16}/><select disabled={busy || !users.length} aria-label="Chọn khách hàng demo" value={user?.id || ''} onChange={e => { const next = users.find(u => u.id === e.target.value); if (next) changeUser(next); }}>{users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select><ChevronDown size={14}/></label>
            <button className={`insights-toggle icon-button ${policyPanelOpen ? 'is-active' : ''}`} aria-label="Thông tin kiểm thử" title="Thông tin kiểm thử" aria-controls="policy-panel" aria-expanded={policyPanelOpen} onClick={() => setPolicyPanelOpen(!policyPanelOpen)}><PanelRight size={20}/></button>
          </div>
        </header>

        <div className="workspace">
          <section className="chat-column" aria-label="Trò chuyện với NovaBank">
            <div className="chat-heading"><div className="assistant-identity"><span className="assistant-symbol"><Sparkles size={20}/></span><div><strong>Nova Assistant</strong><span>Trợ lý ngân hàng của bạn</span></div></div><span className="chat-context">{messages.length > 0 ? activeTitle : 'Luôn sẵn sàng lắng nghe'}</span></div>
            <div className="messages-scroller" ref={scrollerRef}><div className="messages-inner">
              {messages.length === 0 ? (
                <div className="welcome">
                  <div className="welcome-topline"><span className="welcome-kicker"><span className="tiny-spark"><Sparkles size={14}/></span> MỘT CÁCH KẾT NỐI MỚI</span><span className="welcome-edition">NOVABANK / AI</span></div>
                  <div className="welcome-heading"><h1>Xin chào{user ? `, ${user.name.split(' ').slice(-1)[0]}` : ''}.<br/><span>Hôm nay bạn cần giúp gì?</span></h1><div className="welcome-mark" aria-hidden="true"><Landmark size={36} strokeWidth={1.4}/><span><Sparkles size={14}/></span></div></div>
                  <p className="welcome-description">Từ một câu hỏi nhỏ đến việc cần hỗ trợ.<br className="desktop-break"/> Nova luôn ở đây để giúp bạn tìm câu trả lời.</p>
                  <div className="section-caption"><span>BẮT ĐẦU THẬT ĐƠN GIẢN</span><span>Chọn một gợi ý bên dưới <ArrowRight size={14}/></span></div>
                  <div className="suggestions">
                    {suggestions.map((s, index) => (
                      <button key={s.title} className={`suggestion-card tone-${s.tone}`} disabled={!user || busy} onClick={() => { setDraft(s.text); textareaRef.current?.focus(); }}>
                        <div className="suggestion-top"><span className="suggestion-icon">{s.icon}</span><span className="suggestion-number">0{index + 1}</span></div>
                        <strong>{s.title}</strong><span className="suggestion-detail">{s.detail}</span><ArrowUpRight size={19} className="suggestion-arrow"/>
                      </button>
                    ))}
                  </div>
                  <div className="welcome-footnote"><LockKeyhole size={15}/><span>Không nhập thông tin ngân hàng thật. Đây là môi trường trải nghiệm.</span></div>
                </div>
              ) : (
                <div className="chat-thread" role="log" aria-label="Nội dung hội thoại" aria-live="polite">
                  <div className="thread-start"><span/>Bắt đầu cuộc trò chuyện<span/></div>
                  {messages.map(m => (
                    <div className={`message-row ${m.role === 'user' ? 'message-user' : 'message-assistant'}`} key={m.id}>
                      {m.role === 'assistant' && <div className="bot-icon"><Sparkles size={18}/></div>}
                      <div className="message-body"><div className="message-author">{m.role === 'assistant' ? 'Nova Assistant' : 'Bạn'}<span>{formatTime(m.created_at)}</span></div><div className="message-content">{safeMessageParts(m.content)}</div></div>
                      {m.role === 'user' && <div className="me-icon">{user ? getInitials(user.name) : 'U'}</div>}
                    </div>
                  ))}
                  {busy && <div className="message-row message-assistant"><div className="bot-icon"><Bot size={18}/></div><div className="typing" role="status" aria-label="Nova đang trả lời"><span/><span/><span/><small>Nova đang trả lời</small></div></div>}
                </div>
              )}
              <div ref={endRef}/>
            </div></div>

            <div className="composer-area">
              {error && <div className="error-banner" role="alert"><ShieldAlert size={18}/><span>{error}</span><button className="icon-button" aria-label="Đóng thông báo" onClick={() => setError(null)}><X size={17}/></button></div>}
              <div className="composer"><span className="composer-spark"><Sparkles size={20}/></span><textarea id="message-input" ref={textareaRef} rows={1} placeholder="Bạn muốn tìm hiểu điều gì?" value={draft} disabled={!user || busy} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void sendMessage(); } }} aria-label="Tin nhắn"/><button className="send-button" aria-label="Gửi tin nhắn" disabled={!draft.trim() || busy || !user} onClick={() => void sendMessage()}><Send size={19}/></button></div>
              <div className="composer-foot"><span><Shield size={13}/> NovaBank AI · Dữ liệu mô phỏng</span><span><kbd>Enter</kbd> để gửi <span className="foot-divider">·</span> <kbd>Shift + Enter</kbd> xuống dòng</span></div>
            </div>
          </section>

          {policyPanelOpen && <>
            <button className="inspector-overlay" aria-label="Đóng thông tin kiểm thử" onClick={() => setPolicyPanelOpen(false)}/>
            <aside className="inspector" id="policy-panel" aria-label="Thông tin kiểm thử">
              <div className="inspector-header"><div><ShieldCheck size={20}/><strong>Thông tin kiểm thử</strong></div><button className="icon-button" aria-label="Đóng thông tin kiểm thử" onClick={() => setPolicyPanelOpen(false)}><X size={19}/></button></div>
              <div className="inspector-content">
                <div className="inspector-card"><div className="card-kicker"><span className="status-dot"/> KIỂM SOÁT TRUY CẬP</div><h3>Lớp chính sách demo</h3><p>Kiểm tra quyền trước khi thực thi công cụ. Chưa kết nối gateway thực tế của nhóm.</p><div className="stats-row"><div><span>Gateway</span><strong>{health?.gateway_mode ?? '—'}</strong></div><div><span>Mô hình</span><strong>{health?.llm_provider ?? '—'}</strong></div></div></div>
                <div className="panel-section-heading"><Wrench size={16}/> Hoạt động công cụ <span>{events.length}</span></div>
                <div className="activity-list">{events.length === 0 ? <div className="empty-activity"><Database size={25}/><p>Chưa có hoạt động</p><small>Các lần kiểm tra công cụ sẽ xuất hiện ở đây.</small></div> : events.slice(-6).reverse().map(e => <div className="event" key={e.id}><span className={`event-dot ${e.decision === 'ALLOW' ? 'allowed' : 'denied'}`}/><div className="event-content"><strong title={e.tool_name}>{e.tool_name}</strong><span>{e.reason_code.replace(/_/g, ' ')}</span></div><span className={`event-label ${e.decision === 'ALLOW' ? 'allowed' : 'denied'}`}>{e.decision}</span></div>)}</div>
                <div className="panel-section-heading"><Shield size={16}/> Kiểm tra quyền <span className="dryrun-label">DRY RUN</span></div>
                <div className="policy-test"><p>Chỉ kiểm tra quyền truy cập, không thực thi công cụ.</p><label>Công cụ<select value={toolName} onChange={e => { setToolName(e.target.value); setPolicyResult(null); }}><option value="get_account_balance">Kiểm tra số dư</option><option value="get_transaction_status">Tra cứu giao dịch</option><option value="search_banking_faq">Tìm kiếm FAQ</option></select></label>{toolName === 'get_account_balance' && <label>Mã tài khoản<input value={accountId} onChange={e => { setAccountId(e.target.value); setPolicyResult(null); }} placeholder="ACC-ALICE-001"/></label>}{toolName === 'get_transaction_status' && <div className="test-note">Giao dịch demo TX-2001 thuộc tài khoản Bob.</div>}<button className="test-button" onClick={runPolicyDryRun} disabled={!user || busy}>Kiểm tra quyền <ArrowRight size={16}/></button>{policyResult && <div role="status" className={`policy-result ${policyResult.decision.toLowerCase()}`}>{policyResult.decision === 'ALLOW' ? <CheckCheck size={17}/> : <ShieldAlert size={17}/>}<span>{policyResult.decision} · {policyResult.reason_code}</span></div>}</div>
                <div className="inspector-info"><CircleHelp size={17}/><p>Thông tin phục vụ trình diễn kiến trúc, không phải chứng nhận bảo mật ngân hàng.</p></div>
              </div>
            </aside>
          </>}
        </div>
      </main>
    </div>
  );
}
