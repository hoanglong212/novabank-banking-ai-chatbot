import assert from 'node:assert/strict';
import { openerToken } from '../src/components/dev/Outbox';

const ORIGIN = 'http://127.0.0.1:8080';
const stored = (value: unknown) => ({ getItem: (key: string) => key === 'novabank-session' ? JSON.stringify(value) : null });
const opener = (origin: string, value: unknown = { token: 'access.jwt' }) => ({ location: { origin }, sessionStorage: stored(value) });
const tab = (from: ReturnType<typeof opener> | Record<string, unknown> | null) => ({ location: { origin: ORIGIN }, opener: from as never });

export function checkOutboxOpener() {
  assert.equal(openerToken(tab(opener(ORIGIN))), 'access.jwt');
  // A page on another origin that opens /outbox is never read from, even if it exposes a look-alike storage.
  assert.equal(openerToken(tab(opener('http://evil.example'))), null);
  assert.equal(openerToken(tab(opener('http://127.0.0.1:5173'))), null);
  // Real cross-origin openers throw on access; that must fail closed, not crash.
  const crossOrigin = { get location(): never { throw new DOMException('Blocked', 'SecurityError'); }, sessionStorage: stored({ token: 'x' }) };
  assert.equal(openerToken(tab(crossOrigin)), null);
  assert.equal(openerToken(tab(null)), null);
  for (const value of [null, {}, { token: 42 }, { token: '' }]) assert.equal(openerToken(tab(opener(ORIGIN, value))), null);
  const corrupt = { location: { origin: ORIGIN }, sessionStorage: { getItem: () => '{not json' } };
  assert.equal(openerToken(tab(corrupt)), null);
  console.log('PASS: demo inbox borrows a token only from a same-origin opener and fails closed otherwise');
}
