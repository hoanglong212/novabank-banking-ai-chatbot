import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import type { ChatMessage, Conversation, DemoUser, Health, ToolEvent } from '../types';

// Owns session state and request coordination. Presentation components do not call the API.
export function useBankingChat(user: DemoUser) {
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
  const endRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let alive = true;
    api.health().then(status => {
      if (alive) setHealth(status);
    }).catch(err => {
      if (alive) setError(err.message + ' · Unable to connect to the support server.');
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setActive(null);
    setMessages([]);
    setEvents([]);
    setError(null);
    setConversations([]);
    setDraft('');
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

  useEffect(() => {
    if (messages.length === 0 && !busy) {
      scrollerRef.current?.scrollTo({ top: 0 });
      return;
    }
    endRef.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [messages, busy]);

  const refreshConversations = useCallback(async (who: DemoUser) => setConversations(await api.listConversations(who)), []);

  // A new chat is created lazily by the first message, so empty conversations never pile up.
  function startConversation() {
    if (busy) return;
    setActive(null);
    setError(null);
    textareaRef.current?.focus();
  }

  async function deleteConversation(id: string) {
    if (!user || busy || !window.confirm('Delete this conversation?')) return;
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

  async function sendMessage(value = draft, fresh = false) {
    if (!user || busy || !value.trim()) return;
    const content = value.trim();
    setBusy(true);
    setDraft('');
    setError(null);
    try {
      let id = fresh ? null : active;
      if (!id) {
        const created = await api.createConversation(user, content.slice(0, 55));
        id = created.id;
        setActive(created.id);
      }
      // Render local user intent promptly; authoritative history is reloaded after completion.
      setMessages(previous => [...(fresh ? [] : previous), {
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

  const activeTitle = conversations.find(conversation => conversation.id === active)?.title;
  const pickSuggestion = (text: string) => {
    setDraft(text);
    textareaRef.current?.focus();
  };

  return {
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
    endRef,
    scrollerRef,
    textareaRef,
    startConversation,
    deleteConversation,
    sendMessage,
    activeTitle,
    pickSuggestion,
    askNew: (text: string) => sendMessage(text, true),
  };
}
