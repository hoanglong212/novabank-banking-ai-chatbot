import { useSyncExternalStore } from 'react';

function subscribe(listener: () => void) {
  window.addEventListener('popstate', listener);
  return () => window.removeEventListener('popstate', listener);
}
export function navigate(path: string, replace = false) {
  if (!path.startsWith('/') || path.startsWith('//') || /[?#\\]/.test(path)) throw new Error('Invalid application path');
  window.history[replace ? 'replaceState' : 'pushState'](null, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}
export function usePath() {
  return useSyncExternalStore(subscribe, () => window.location.pathname, () => '/');
}
