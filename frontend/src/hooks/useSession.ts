import { useCallback, useEffect, useState } from 'react';
import { api, setUnauthorizedHandler } from '../api';
import type { DemoUser } from '../types';

const KEY = 'novabank-session';

// sessionStorage: the JWT dies with the tab and is never sent automatically (no CSRF surface).
function restore(): DemoUser | null {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(KEY) || 'null') as (DemoUser & { expiresAt: number }) | null;
    return saved && saved.expiresAt > Date.now() ? saved : null;
  } catch {
    return null;
  }
}

export function useSession() {
  const [user, setUser] = useState<DemoUser | null>(restore);
  const [notice, setNotice] = useState<string | null>(null);

  const logout = useCallback((message: string | null = null) => {
    window.sessionStorage.removeItem(KEY);
    setUser(null);
    setNotice(message);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => logout('Your session has ended. Please sign in again.'));
  }, [logout]);

  async function login(username: string, password: string) {
    const result = await api.login(username, password);
    const next = { id: result.user.id, name: result.user.name, token: result.access_token };
    window.sessionStorage.setItem(KEY, JSON.stringify({ ...next, expiresAt: Date.now() + result.expires_in * 1000 }));
    setNotice(null);
    setUser(next);
  }

  return { user, notice, login, logout };
}
