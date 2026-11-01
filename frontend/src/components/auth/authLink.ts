export type AuthLink = { mode: 'verify' | 'reset'; token: string };

// Pure parsing: callers remove the fragment in an effect, safe under StrictMode.
export function parseAuthLink(hash: string): AuthLink | null {
  const [route, params] = hash.slice(1).split('?', 2);
  if (route !== 'verify-email' && route !== 'reset-password') return null;
  const candidate = new URLSearchParams(params).get('token') || '';
  return { mode: route === 'verify-email' ? 'verify' : 'reset', token: /^[A-Za-z0-9_-]{43}$/.test(candidate) ? candidate : '' };
}
