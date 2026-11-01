import type { DemoUser, LoginResponse } from './types';

const KEY = 'novabank-session';
const ENDED = 'Your session has ended. Please sign in again.';
interface Session {
  user: DemoUser; sessionId: string; accessToken: string; refreshToken: string;
  accessExpiresAt: number; idleExpiresAt: number; absoluteExpiresAt: number;
}
const listeners = new Set<() => void>();
let notice: string | null = null;
let generation = 0;
let rotation: { generation: number; promise: Promise<void> } | null = null;
let lastActivityAttempt = -Infinity;

function restore(): Session | null {
  try {
    if (typeof window === 'undefined') return null;
    const saved = JSON.parse(window.sessionStorage.getItem(KEY) || 'null');
    if (saved?.version === 2 && typeof saved.id === 'string' && typeof saved.name === 'string'
      && typeof saved.token === 'string' && typeof saved.refreshToken === 'string' && typeof saved.sessionId === 'string'
      && Number.isFinite(saved.expiresAt) && Number.isFinite(saved.idleExpiresAt) && Number.isFinite(saved.absoluteExpiresAt)
      && Math.min(saved.idleExpiresAt, saved.absoluteExpiresAt) > Date.now()) {
      return { user: { id: saved.id, name: saved.name, token: saved.token, sessionId: saved.sessionId,
        role: saved.role, permissions: saved.permissions }, sessionId: saved.sessionId,
        accessToken: saved.token, refreshToken: saved.refreshToken, accessExpiresAt: saved.expiresAt,
        idleExpiresAt: saved.idleExpiresAt, absoluteExpiresAt: saved.absoluteExpiresAt };
    }
    window.sessionStorage.removeItem(KEY);
  } catch { /* Invalid or inaccessible browser storage requires a new sign-in. */ }
  return null;
}

let session = restore();
export const currentSession = () => session;
export const sessionUser = () => session?.user ?? null;
export const sessionNotice = () => notice;
export function subscribeSession(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

function publish() {
  try {
    if (typeof window !== 'undefined') {
      if (session) window.sessionStorage.setItem(KEY, JSON.stringify({ ...session.user, version: 2,
        token: session.accessToken, refreshToken: session.refreshToken, sessionId: session.sessionId,
        expiresAt: session.accessExpiresAt, idleExpiresAt: session.idleExpiresAt, absoluteExpiresAt: session.absoluteExpiresAt }));
      else window.sessionStorage.removeItem(KEY);
    }
  } catch { /* The in-memory session still works until this tab closes. */ }
  listeners.forEach(listener => listener());
}

function validate(value: LoginResponse) {
  if (!value || typeof value.access_token !== 'string' || !value.access_token
    || typeof value.refresh_token !== 'string' || !value.refresh_token || typeof value.session_id !== 'string' || !value.session_id
    || typeof value.user?.id !== 'string' || typeof value.user.name !== 'string'
    || !Number.isFinite(value.expires_in) || value.expires_in <= 0
    || !Number.isFinite(value.idle_expires_at) || !Number.isFinite(value.absolute_expires_at)
    || Math.min(value.idle_expires_at, value.absolute_expires_at) * 1000 <= Date.now()) {
    throw new Error('Invalid sign-in response. Please sign in again.');
  }
}

export function acceptSession(value: LoginResponse) {
  validate(value);
  generation++;
  lastActivityAttempt = -Infinity;
  session = { user: { ...value.user, token: value.access_token, sessionId: value.session_id },
    sessionId: value.session_id, accessToken: value.access_token, refreshToken: value.refresh_token,
    accessExpiresAt: Date.now() + value.expires_in * 1000, idleExpiresAt: value.idle_expires_at * 1000,
    absoluteExpiresAt: value.absolute_expires_at * 1000 };
  notice = null;
  publish();
}

export function clearSession(message: string | null = null) {
  generation++;
  session = null;
  notice = message;
  publish();
}

export function expireIfIdle() {
  if (session && Date.now() >= Math.min(session.idleExpiresAt, session.absoluteExpiresAt)) {
    clearSession('You were signed out because your session expired. Please sign in again.');
    return true;
  }
  return false;
}

export function isCurrentSession(user: DemoUser) {
  return !!session && !!user.sessionId && session.sessionId === user.sessionId && session.user.id === user.id;
}

export function assertSession(user: DemoUser) {
  expireIfIdle();
  if (!isCurrentSession(user)) throw new Error(ENDED);
}

export function endSession(user: DemoUser) {
  if (isCurrentSession(user)) clearSession(ENDED);
}

export async function refreshSession(): Promise<void> {
  expireIfIdle();
  if (!session) throw new Error(ENDED);
  if (rotation?.generation === generation) return rotation.promise;
  const prior = session;
  const started = generation;
  const promise = (async () => {
    try {
      const response = await fetch('/api/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: prior.refreshToken }), signal: AbortSignal.timeout(10_000) });
      if (!response.ok) throw new Error(ENDED);
      const value: LoginResponse = await response.json();
      if (generation !== started || !isCurrentSession(prior.user) || expireIfIdle()) throw new Error(ENDED);
      validate(value);
      if (value.session_id !== prior.sessionId || value.user.id !== prior.user.id) throw new Error(ENDED);
      // Keep the user reference stable so token rotation does not reset chat/forms or restart queries.
      session = { ...session!, accessToken: value.access_token, refreshToken: value.refresh_token,
        accessExpiresAt: Date.now() + value.expires_in * 1000,
        idleExpiresAt: Math.max(session!.idleExpiresAt, value.idle_expires_at * 1000),
        absoluteExpiresAt: Math.min(session!.absoluteExpiresAt, value.absolute_expires_at * 1000) };
      publish();
    } catch (error) {
      // A lost refresh response may already have consumed the single-use token. Never replay it.
      if (generation === started) clearSession(ENDED);
      throw error;
    } finally {
      if (rotation?.generation === started) rotation = null;
    }
  })();
  rotation = { generation: started, promise };
  return promise;
}

export async function sessionToken(user: DemoUser): Promise<string> {
  assertSession(user);
  if (session!.accessExpiresAt <= Date.now() + 15_000) await refreshSession();
  assertSession(user);
  return session!.accessToken;
}

// Called only from browser input handlers. API reads, timers and refresh never count as activity.
export async function recordActivity() {
  if (expireIfIdle() || !session || Date.now() - lastActivityAttempt < 30_000) return;
  const prior = session;
  const started = generation;
  lastActivityAttempt = Date.now();
  try {
    const token = await sessionToken(prior.user);
    const response = await fetch('/api/auth/activity', { method: 'POST', headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(10_000) });
    if (generation !== started || !isCurrentSession(prior.user) || expireIfIdle()) return;
    if (response.status === 401) { endSession(prior.user); return; }
    if (!response.ok) return;
    const value = await response.json();
    if (generation !== started || !isCurrentSession(prior.user) || expireIfIdle()) return;
    if (Number.isFinite(value.idle_expires_at)) {
      session = { ...session!, idleExpiresAt: Math.min(session!.absoluteExpiresAt,
        Math.max(session!.idleExpiresAt, value.idle_expires_at * 1000)) };
      publish();
    }
  } catch { /* No acknowledgement means no extension; the server remains authoritative. */ }
}
