import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import type { ChatMessage, Conversation, DemoUser, Health, ToolEvent, Decision } from '../types';

// Owns session state and request coordination. Presentation components do not call the API.
export function useBankingChat() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [user, setUser] = useState<DemoUser | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selection, setSelection] = useState<{ id: string; ownerId: string; } | null>(null);
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
    }).catch(err => {
      if (alive) setError(err.message + ' · Unable to connect to the support server.');
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    window.sessionStorage.setItem('novabank-demo-user', user.id);
    let cancelled = false;
    setActive(null);
    setMessages([]);
    setEvents([]);
    setError(null);
    setConversations([]);
    setDraft('');
    setPolicyResult(null);
    api.listConversations(user).then(list => {
      if (cancelled) return;
      setConversations(list);
      if (list[0]) setActive(list[0].id);
    }).catch(err => {
      if (!cancelled) setError(err.message);
    });
    return () => {
      cancelled = true;
    };
  }, [user, setActive]);

  useEffect(() => {
    if (!user || !active) {
      setMessages([]);
      setEvents([]);
      return;
    }
    let cancelled = false;
    Promise.all([api.messages(user, active), api.toolEvents(user, active)]).then(([chat, log]) => {
      if (cancelled) return;
      setMessages(chat);
      setEvents(log);
    }).catch(err => {
      if (!cancelled) setError(err.message);
    });
    return () => {
      cancelled = true;
    };
  }, [user, active]);

  function changeUser(next: DemoUser) {
    if (busy || next.id === user?.id) return;
    setSelection(null);
    setMessages([]);
    setEvents([]);
    setConversations([]);
    setDraft('');
    setPolicyResult(null);
    setError(null);
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
      if (event.key === 'Escape') {
        setSidebarOpen(false);
        setPolicyPanelOpen(false);
      }
    }
    window.addEventListener('keydown', closePanels);
    return () => window.removeEventListener('keydown', closePanels);
  }, []);
  const refreshConversations = useCallback(async (who: DemoUser) => setConversations(await api.listConversations(who)), []);

  async function startConversation() {
    if (!user || busy) return;
    setError(null);
    setBusy(true);
    try {
      const created = await api.createConversation(user, 'New conversation');
      await refreshConversations(user);
      setActive(created.id);
      setSidebarOpen(false);
      textareaRef.current?.focus();
    } catch (err) {
      setError((err as Error).message);
    }
    finally {
      setBusy(false);
    }
  }

  async function deleteConversation(id: string) {
    if (!user || busy || !window.confirm('Delete this demo conversation?')) return;
    setBusy(true);
    try {
      await api.deleteConversation(user, id);
      const fresh = await api.listConversations(user);
      setConversations(fresh);
      if (active === id) setActive(fresh[0]?.id ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
    finally {
      setBusy(false);
    }
  }

  async function sendMessage(value = draft) {
    if (!user || busy || !value.trim()) return;
    const content = value.trim();
    setBusy(true);
    setDraft('');
    setError(null);
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
      setMessages(chat);
      setEvents(log);
      await refreshConversations(user);
      if (response.message.role !== 'assistant') throw new Error('Unexpected backend response');
    } catch (err) {
      setError((err as Error).message + ' · Your message may have been saved. Check the conversation before sending it again.');
      if (active) api.messages(user, active).then(setMessages).catch(() => { });
    } finally {
      setBusy(false);
    }
  }

  async function runPolicyDryRun() {
    if (!user || busy) return;
    setPolicyResult(null);
    setError(null);
    setBusy(true);
    try {
      let id = active;
      if (!id) {
        const created = await api.createConversation(user, 'Policy test');
        id = created.id;
        setActive(id);
      }
      const args: Record<string, unknown> = toolName === 'get_account_balance'
        ? { account_id: accountId.trim() || undefined }
        : toolName === 'get_transaction_status'
          ? { transaction_id: 'TX-2001' }
          : { query: 'What is VietQR?' };
      const response = await api.policyDryRun(user, id, toolName, args);
      setPolicyResult(response);
      setEvents(await api.toolEvents(user, id));
      await refreshConversations(user);
    } catch (err) {
      setError((err as Error).message);
    }
    finally {
      setBusy(false);
    }
  }
  const activeTitle = conversations.find(conversation => conversation.id === active)?.title;
  const pickSuggestion = (text: string) => {
    setDraft(text);
    textareaRef.current?.focus();
  };

  return {
    users,
    user,
    conversations,
    active,
    setActive,
    messages,
    events,
    health,
    draft,
    setDraft,
    busy,
    error,
    setError,
    sidebarOpen,
    setSidebarOpen,
    policyPanelOpen,
    setPolicyPanelOpen,
    toolName,
    setToolName,
    accountId,
    setAccountId,
    policyResult,
    setPolicyResult,
    endRef,
    scrollerRef,
    textareaRef,
    changeUser,
    startConversation,
    deleteConversation,
    sendMessage,
    runPolicyDryRun,
    activeTitle,
    pickSuggestion
  };
}
