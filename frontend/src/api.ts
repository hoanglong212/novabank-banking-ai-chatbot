import type { Conversation, ChatMessage, DemoUser, ToolEvent, SendResponse, Health, Decision, Session, BankAccount, BankTransaction, TransferIntent } from './types';

const PREFIX = '/api';
let csrf = '';

async function request<T>(path: string, _user?: DemoUser, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.method && options.method !== 'GET' && csrf) headers.set('X-CSRF-Token', csrf);
  if (options.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(PREFIX + path, { ...options, headers, credentials: 'same-origin' });
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') {
      csrf = '';
      window.dispatchEvent(new Event('novabank-session-expired'));
    }
    let reason = `Request failed (${response.status})`;
    try { const problem = await response.json(); if (typeof problem.detail === 'string') reason = problem.detail; } catch { /* ignore */ }
    throw Object.assign(new Error(reason), { status: response.status });
  }
  return response.json() as Promise<T>;
}

export const api = {
  accounts: () => request<BankAccount[]>('/accounts'),
  transactions: () => request<BankTransaction[]>('/transactions'),
  transferIntent: (id: string) => request<TransferIntent>(`/transfers/intents/${encodeURIComponent(id)}`),
  previewTransfer: (payload: { source_account_id: string; recipient_account_id: string; amount_vnd: number; description: string }) =>
    request<TransferIntent>('/transfers/intents',undefined,{method:'POST',body:JSON.stringify(payload)}),
  confirmTransfer: (id: string) => request<BankTransaction>(`/transfers/intents/${encodeURIComponent(id)}/confirm`,undefined,{method:'POST',body:'{}'}),
  cancelTransfer: (id: string) => request<{ cancelled: boolean }>(`/transfers/intents/${encodeURIComponent(id)}/cancel`,undefined,{method:'POST',body:'{}'}),
  session: async () => {
    try {
      const session = await request<Session>('/auth/session');
      csrf = session.csrf_token;
      return session;
    } catch (error) {
      if ((error as { status?: number }).status === 401) return null;
      throw error;
    }
  },
  login: async (username: string, password: string) => {
    const session = await request<Session>('/auth/login', undefined, { method: 'POST', body: JSON.stringify({ username, password }) });
    csrf = session.csrf_token;
    return session;
  },
  logout: async () => {
    await request('/auth/logout', undefined, { method: 'POST' });
    csrf = '';
  },
  health: () => request<Health>('/health'),
  listConversations: (user: DemoUser) => request<Conversation[]>('/conversations', user),
  createConversation: (user: DemoUser, title = 'New conversation') =>
    request<Conversation>('/conversations', user, { method: 'POST', body: JSON.stringify({ title }) }),
  deleteConversation: (user: DemoUser, id: string) =>
    request<{ deleted: boolean }>(`/conversations/${encodeURIComponent(id)}`, user, { method: 'DELETE' }),
  messages: (user: DemoUser, id: string) => request<ChatMessage[]>(`/conversations/${encodeURIComponent(id)}/messages`, user),
  toolEvents: (user: DemoUser, id: string) => request<ToolEvent[]>(`/conversations/${encodeURIComponent(id)}/tool-events`, user),
  sendMessage: (user: DemoUser, id: string, content: string) =>
    request<SendResponse>(`/conversations/${encodeURIComponent(id)}/messages`, user, {
      method: 'POST', body: JSON.stringify({ content }),
    }),
  policyDryRun: (user: DemoUser, id: string, tool_name: string, args: Record<string, unknown>) =>
    request<Decision>(`/conversations/${encodeURIComponent(id)}/demo/tool-check`, user, {
      method: 'POST', body: JSON.stringify({ tool_name, arguments: args }),
    }),
};
