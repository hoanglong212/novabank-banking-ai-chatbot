import { useCallback, useEffect, useSyncExternalStore } from 'react';
import { api } from '../api';
import { acceptSession, clearSession, currentSession, expireIfIdle, isCurrentSession, recordActivity,
  sessionNotice, sessionUser, subscribeSession } from '../sessionStore';

export function useSession() {
  const user = useSyncExternalStore(subscribeSession, sessionUser, () => null);
  const notice = useSyncExternalStore(subscribeSession, sessionNotice, () => null);
  const logout = useCallback(async () => {
    const prior = currentSession();
    if (!prior) { clearSession(); return; }
    let message: string | null = null;
    try { await api.logout(prior.user); }
    catch { message = 'Signed out on this tab. If the server was unavailable, the other session controls can end this session.'; }
    if (isCurrentSession(prior.user)) clearSession(message);
  }, []);

  useEffect(() => {
    const check = () => { expireIfIdle(); };
    const activity = (event: Event) => {
      if (event.isTrusted && document.visibilityState === 'visible') void recordActivity();
    };
    check();
    const timer = window.setInterval(check, 1000);
    document.addEventListener('visibilitychange', check);
    window.addEventListener('focus', check);
    for (const name of ['pointerdown', 'keydown', 'scroll']) window.addEventListener(name, activity, { passive: true, capture: true });
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', check);
      window.removeEventListener('focus', check);
      for (const name of ['pointerdown', 'keydown', 'scroll']) window.removeEventListener(name, activity, true);
    };
  }, []);
  return { user, notice, login: api.login, completeLogin: acceptSession, logout };
}
