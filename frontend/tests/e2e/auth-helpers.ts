import { expect, type Locator, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { createHmac } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve, relative } from 'node:path';

export function clearAuthRequestBudget() {
  // Shared E2E server only. Production rate limits are tested without resets in pytest.
  const root = resolve('..');
  const db = resolve(JSON.parse(readFileSync(resolve(root, '.local/e2e/latest.json'), 'utf8')).db_path);
  if (relative(resolve(root, '.local/e2e'), db).startsWith('..')) throw new Error('Expected disposable E2E database');
  const venv = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
  const python = process.env.NOVABANK_PYTHON || (existsSync(venv) ? venv : 'python');
  execFileSync(python, ['-c', "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"DELETE FROM identity_limits WHERE scope LIKE 'request:/api/auth/%'\"); c.commit(); c.close()", db]);
}

export function localMessage(email: string, kind: string) {
  const root = resolve('..');
  const db = JSON.parse(readFileSync(resolve(root, '.local/e2e/latest.json'), 'utf8')).db_path;
  const venv = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
  const python = process.env.NOVABANK_PYTHON || (existsSync(venv) ? venv : 'python');
  const cli = resolve(root, 'scripts/dev-outbox.py');
  const rows = JSON.parse(execFileSync(python, [cli, '--db', db, '--email', email], { encoding: 'utf8' }));
  const row = rows.find((r: { kind: string }) => r.kind === kind);
  expect(row).toBeTruthy();
  return JSON.parse(execFileSync(python, [cli, '--db', db, '--id', row.id, '--origin', 'http://127.0.0.1:8092'], { encoding: 'utf8' }));
}

export async function completeEmailMfa(page: Page, email: string) {
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
  await page.getByLabel('Verification code', { exact: true }).fill(localMessage(email, 'LOGIN_OTP').code);
  await page.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
}

export async function beginDemoLogin(page: Page, username: string) {
  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(username[0].toUpperCase() + username.slice(1) + '@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
}

export async function demoLogin(page: Page, username: string) {
  await beginDemoLogin(page, username);
  await completeEmailMfa(page, username + '@novabank.test');
}

// Independent RFC 6238 authenticator for tests (base32 secret, SHA-1, 6 digits, 30 s).
export function authenticatorCode(secret: string, stepOffset = 0) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret].map(character => alphabet.indexOf(character).toString(2).padStart(5, '0')).join('');
  const bytes = Buffer.from(bits.match(/.{8}/g)!.map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + stepOffset));
  const mac = createHmac('sha1', bytes).update(counter).digest();
  const offset = mac[mac.length - 1] & 15;
  return String((mac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, '0');
}

// Demo customers get this transaction PIN the first time a test confirms a payment.
export const DEMO_PIN = '482916';
const demoPassword = (username: string) => username.charAt(0).toUpperCase() + username.slice(1) + '@2026';

/** Confirm with the transaction PIN, creating it first if this account has none yet (test order varies). */
export async function enterTransactionPin(scope: Page | Locator, username: string) {
  const field = scope.getByLabel('Transaction PIN', { exact: true });
  const create = scope.getByLabel('New 6-digit PIN', { exact: true });
  const either = field.or(create);
  await expect(either).toBeVisible();
  // The create-PIN input is autocomplete="new-password"; read it from whichever input rendered.
  if (await either.getAttribute('autocomplete') === 'new-password') {
    await scope.getByLabel('Current password', { exact: true }).fill(demoPassword(username));
    await create.fill(DEMO_PIN);
    await scope.getByLabel('Repeat PIN', { exact: true }).fill(DEMO_PIN);
    await scope.getByRole('button', { name: 'Save PIN and continue', exact: true }).click();
  }
  await field.fill(DEMO_PIN);
}

/** API-level confirmations: the PIN once set, otherwise the emailed code. */
export function transactionCode(draft: { otp_method?: string; method?: string }, email: string, kind: string) {
  return (draft.otp_method ?? draft.method) === 'pin' ? DEMO_PIN : localMessage(email, kind).code;
}
