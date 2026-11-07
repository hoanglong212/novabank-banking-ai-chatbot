import type { Conversation, ChatMessage, DemoUser, ToolEvent, SendResponse, Health, Decision, LoginResponse, Profile, Bank, VietQR, Transfer } from './types';
import type { Page, Transaction, TransactionFilters, NotificationPage, BankNotification, AuditEvent, Announcement, NotificationCategory } from './types';
import type { MfaChallenge, UserSession, LoginAttempt, MfaStatus, TotpSetup } from './types';
import { assertSession, currentSession, endSession, refreshSession, sessionToken } from './sessionStore';

const PREFIX = '/api';
const DEVICE_KEY = 'novabank.device';
function deviceToken() {
  try { return localStorage.getItem(DEVICE_KEY) || undefined; } catch { return undefined; }
}
export async function responseFor(path: string, user?: DemoUser, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  const token = user ? await sessionToken(user) : null;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body) headers.set('Content-Type', 'application/json');
  let response = await fetch(PREFIX + path, { ...options, headers });
  if (user) {
    assertSession(user);
    // Authentication rejects before route side effects. Retry a 401 once with rotated credentials.
    if (response.status === 401) {
      if (currentSession()?.accessToken === token) await refreshSession();
      headers.set('Authorization', `Bearer ${await sessionToken(user)}`);
      response = await fetch(PREFIX + path, { ...options, headers });
      assertSession(user);
    }
  }
  if (!response.ok) {
    let reason = `Request failed (${response.status})`;
    try { const problem = await response.json(); if (typeof problem.detail === 'string') reason = problem.detail; } catch { /* ignore */ }
    if (response.status === 401 && user) endSession(user);
    throw new Error(reason);
  }
  return response;
}

export async function request<T>(path: string, user?: DemoUser, options: RequestInit = {}): Promise<T> {
  return (await responseFor(path, user, options)).json() as Promise<T>;
}

export async function streamMessage(user: DemoUser, id: string, content: string, profile: 'baseline' | 'defended', progress: (text: string) => void,
  options: { signal?: AbortSignal; text?: (text: string) => void; run?: (id: string) => void } = {}): Promise<SendResponse> {
  const response = await responseFor(`/conversations/${encodeURIComponent(id)}/stream`, user, {
    method: 'POST', body: JSON.stringify({ content, profile }), signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(150_000)]) : AbortSignal.timeout(150_000),
  });
  const reader = response.body?.getReader();
  if (!reader) throw new Error('Streaming is unavailable.');
  const decoder = new TextDecoder(); let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read(); assertSession(user);
      buffer += decoder.decode(value, { stream: !done }).replaceAll('\r\n', '\n');
      if (buffer.length > 1000000) throw new Error('Assistant response exceeded its limit.');
      let end: number;
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, end); buffer = buffer.slice(end + 2);
        const event = frame.split('\n').find(line => line.startsWith('event: '))?.slice(7);
        const raw = frame.split('\n').filter(line => line.startsWith('data: ')).map(line => line.slice(6)).join('\n');
        if (!raw) continue;
        const data = JSON.parse(raw);
        if (event === 'run') options.run?.(data.run_id);
        if (event === 'text') options.text?.(data.text);
        if (event === 'complete') return data as SendResponse;
        if (event === 'error') throw new Error(data.message || 'Assistant request failed.');
        if (event === 'tool') progress(`${data.status === 'running' ? 'Checking' : 'Checked'} ${String(data.name).replaceAll('_', ' ')}…`);
        if (event === 'progress') progress(data.stage === 'generating' ? 'Writing a response…' : 'Thinking…');
      }
      if (done) break;
    }
    throw new Error('The assistant stream ended before completion.');
  } finally { await reader.cancel(); }
}

function query(filters: TransactionFilters | Record<string, string | number | boolean | undefined>) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  return params.toString();
}

export const api = {
  health: () => request<Health>('/health'),
  // A trusted device (set after one MFA sign-in) may return a session directly instead of a challenge.
  login: (username: string, password: string) =>
    request<MfaChallenge | LoginResponse>('/auth/login', undefined, { method: 'POST', body: JSON.stringify({ username, password, device_token: deviceToken() }) }),
  verifyMfa: async (challenge_id: string, code: string) => {
    const result = await request<LoginResponse>('/auth/mfa/verify', undefined, { method: 'POST', body: JSON.stringify({ challenge_id, code }) });
    if (result.device_token) try { localStorage.setItem(DEVICE_KEY, result.device_token); } catch { /* Storage may be disabled. */ }
    return result;
  },
  resendMfa: (challenge_id: string) =>
    request<{ method: 'email'; message: string }>('/auth/mfa/email', undefined, { method: 'POST', body: JSON.stringify({ challenge_id }) }),
  logout: (user: DemoUser) => request<{ message: string }>('/auth/logout', user, { method: 'POST', signal: AbortSignal.timeout(10_000) }),
  sessions: (user: DemoUser) => request<{ items: UserSession[] }>('/auth/sessions', user),
  revokeSession: (user: DemoUser, id: string) => request<{ message: string }>(`/auth/sessions/${encodeURIComponent(id)}`, user, { method: 'DELETE' }),
  loginHistory: (user: DemoUser, offset = 0) => request<Page<LoginAttempt>>(`/auth/login-history?limit=10&offset=${offset}`, user),
  mfaStatus: (user: DemoUser) => request<MfaStatus>('/auth/mfa', user),
  setPin: (user: DemoUser, password: string, pin: string) =>
    request<{ message: string }>('/auth/pin', user, { method: 'POST', body: JSON.stringify({ password, pin }) }),
  setupTotp: (user: DemoUser, password: string) => request<TotpSetup>('/auth/mfa/setup', user, { method: 'POST', body: JSON.stringify({ password }) }),
  enableTotp: (user: DemoUser, code: string) => request<{ message: string }>('/auth/mfa/enable', user, { method: 'POST', body: JSON.stringify({ code }) }),
  disableTotpRequest: (user: DemoUser, password: string) => request<MfaChallenge>('/auth/mfa/disable-request', user, { method: 'POST', body: JSON.stringify({ password }) }),
  disableTotp: (user: DemoUser, challenge_id: string, code: string) => request<{ message: string }>('/auth/mfa/disable', user, { method: 'POST', body: JSON.stringify({ challenge_id, code }) }),
  register: (body: { username: string; name: string; email: string; password: string }) =>
    request<{ message: string }>('/auth/register', undefined, { method: 'POST', body: JSON.stringify(body) }),
  resendVerification: (email: string) =>
    request<{ message: string }>('/auth/resend-verification', undefined, { method: 'POST', body: JSON.stringify({ email }) }),
  verifyEmail: (token: string) =>
    request<{ message: string }>('/auth/verify-email', undefined, { method: 'POST', body: JSON.stringify({ token }) }),
  forgotPassword: (email: string) =>
    request<{ message: string }>('/auth/forgot-password', undefined, { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) =>
    request<{ message: string }>('/auth/reset-password', undefined, { method: 'POST', body: JSON.stringify({ token, password }) }),
  me: (user: DemoUser) => request<Profile>('/me', user),
  transactions: (user: DemoUser, filters: TransactionFilters = {}) =>
    request<Page<Transaction>>('/transactions?' + query(filters), user),
  transaction: (user: DemoUser, id: string) => request<Transaction>('/transactions/' + encodeURIComponent(id), user),
  receipt: async (user: DemoUser, id: string) =>
    (await responseFor('/transactions/' + encodeURIComponent(id) + '/receipt.pdf', user)).blob(),
  notifications: (user: DemoUser, offset = 0, category?: NotificationCategory, filters: { q?: string; unread?: boolean } = {}) =>
    request<NotificationPage>('/notifications?' + query({ offset, category, q: filters.q, unread: filters.unread || undefined }), user),
  announcements: (user: DemoUser) => request<{ items: Announcement[] }>('/announcements', user),
  readNotification: (user: DemoUser, id: string) =>
    request<BankNotification>(`/notifications/${encodeURIComponent(id)}/read`, user, { method: 'PATCH' }),
  readAllNotifications: (user: DemoUser, category?: NotificationCategory) =>
    request<{ updated: number }>('/notifications/read-all' + (category ? `?category=${category}` : ''), user, { method: 'POST' }),
  adminTransactions: (user: DemoUser, filters: TransactionFilters = {}) =>
    request<Page<Transaction>>('/admin/transactions?' + query(filters), user),
  transferAudit: (user: DemoUser, id: string) =>
    request<{ items: AuditEvent[] }>(`/admin/transfers/${encodeURIComponent(id)}/audit`, user),
  banks: (user: DemoUser) => request<Bank[]>('/vietqr/banks', user),
  createVietQR: (user: DemoUser, body: Record<string, unknown>) =>
    request<VietQR>('/vietqr', user, { method: 'POST', body: JSON.stringify(body) }),
  createTransfer: (user: DemoUser, body: Record<string, unknown>) =>
    request<Transfer>('/transfers', user, { method: 'POST', body: JSON.stringify(body) }),
  resendOtp: (user: DemoUser, id: string) =>
    request<Transfer>(`/transfers/${encodeURIComponent(id)}/otp`, user, { method: 'POST' }),
  confirmTransfer: (user: DemoUser, id: string, otp: string, idempotencyKey: string) =>
    request<Transfer>(`/transfers/${encodeURIComponent(id)}/confirm`, user, {
      method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ otp }),
    }),
  listConversations: (user: DemoUser) => request<Conversation[]>('/conversations', user),
  createConversation: (user: DemoUser, title = 'New conversation') =>
    request<Conversation>('/conversations', user, { method: 'POST', body: JSON.stringify({ title }) }),
  deleteConversation: (user: DemoUser, id: string) =>
    request<{ deleted: boolean }>(`/conversations/${encodeURIComponent(id)}`, user, { method: 'DELETE' }),
  messages: (user: DemoUser, id: string) => request<ChatMessage[]>(`/conversations/${encodeURIComponent(id)}/messages`, user),
  toolEvents: (user: DemoUser, id: string) => request<ToolEvent[]>(`/conversations/${encodeURIComponent(id)}/tool-events`, user),
  cancelRun: (user: DemoUser, id: string) => request<{ status: string }>(`/agent/runs/${encodeURIComponent(id)}/cancel`, user, { method: 'POST', signal: AbortSignal.timeout(10_000) }),
  sendMessage: (user: DemoUser, id: string, content: string, signal?: AbortSignal) =>
    request<SendResponse>(`/conversations/${encodeURIComponent(id)}/messages`, user, {
      method: 'POST', body: JSON.stringify({ content }), signal,
    }),
  policyDryRun: (user: DemoUser, id: string, tool_name: string, args: Record<string, unknown>) =>
    request<Decision>(`/conversations/${encodeURIComponent(id)}/demo/tool-check`, user, {
      method: 'POST', body: JSON.stringify({ tool_name, arguments: args }),
    }),
};
