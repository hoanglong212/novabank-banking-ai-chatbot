import type { Conversation, ChatMessage, DemoUser, ToolEvent, SendResponse, Health, Decision, LoginResponse, Profile, Bank, VietQR } from './types';

const PREFIX = '/api';
let onUnauthorized: () => void = () => { };

// The session hook registers this so any expired or rejected JWT signs the customer out.
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

async function request<T>(path: string, user?: DemoUser, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (user) headers.set('Authorization', `Bearer ${user.token}`);
  if (options.body) headers.set('Content-Type', 'application/json');
  const response = await fetch(PREFIX + path, { ...options, headers });
  if (!response.ok) {
    let reason = `Request failed (${response.status})`;
    try { const problem = await response.json(); if (typeof problem.detail === 'string') reason = problem.detail; } catch { /* ignore */ }
    if (response.status === 401 && user) onUnauthorized();
    throw new Error(reason);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>('/health'),
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', undefined, { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: (user: DemoUser) => request<Profile>('/me', user),
  banks: (user: DemoUser) => request<Bank[]>('/vietqr/banks', user),
  createVietQR: (user: DemoUser, body: Record<string, unknown>) =>
    request<VietQR>('/vietqr', user, { method: 'POST', body: JSON.stringify(body) }),
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
