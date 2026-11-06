// Record real local UI actions using fictional accounts; do not confirm payments.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const origin = process.env.NOVABANK_URL || 'http://127.0.0.1:8081';
const out = resolve('../docs/release/week7-evidence/media');
const scratch = resolve('../.local/week7-deploy/videos');
await mkdir(out, { recursive: true });
await mkdir(scratch, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: scratch, size: { width: 1440, height: 1000 } } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const frames = [];
async function hold(label) {
  frames.push({ label, url: page.url() });
  await page.waitForTimeout(1400);
}
try {
  await page.goto(origin);
  await page.getByLabel('Username', { exact: true }).fill('alice');
  await page.getByLabel('Password', { exact: true }).fill('Alice@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in' })).toBeVisible();
  await hold('Login requests MFA');
  await page.goto(origin + '/outbox');
  await page.getByRole('button', { name: /LOGIN_OTP/ }).first().click();
  const code = await page.getByTestId('outbox-code').innerText();
  await hold('Demo mailbox contains login code');
  // Navigating away loses the pending React challenge. Request a new challenge
  // and retrieve its current message; the previously shown code is not reused.
  await page.goto(origin);
  await page.getByLabel('Username', { exact: true }).fill('alice');
  await page.getByLabel('Password', { exact: true }).fill('Alice@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in' })).toBeVisible();
  const rows = await (await page.request.get(origin + '/api/dev/outbox')).json();
  const mail = rows.items.find(row => row.kind === 'LOGIN_OTP');
  const detail = await (await page.request.get(origin + '/api/dev/outbox/' + mail.id)).json();
  expect(code).toMatch(/^\d{6}$/);
  await page.getByLabel('Verification code', { exact: true }).fill(detail.code);
  await page.getByRole('button', { name: 'Verify and sign in' }).click();
  await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
  await hold('MFA login accepted');
  await page.goto(origin + '/transfer/new');
  await page.getByLabel('NovaBank account ID').fill('ACC-BOB-001');
  await page.getByRole('textbox', { name: 'Amount', exact: true }).fill('10000');
  const drafted = page.waitForResponse(r => r.url().endsWith('/api/transfers') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  const response = await drafted;
  const draft = await response.json();
  expect(draft).not.toHaveProperty('demo_otp');
  await writeFile(resolve(out, 'transfer-response.json'), JSON.stringify({ status: response.status(), body: draft }, null, 2));
  await hold('Transfer review; response has no demo_otp');
  await page.getByRole('button', { name: 'Continue to verification' }).click();
  await hold('Separate OTP page; no payment confirmed');
  await page.goto(origin + '/outbox');
  await page.getByRole('button', { name: /TRANSFER_OTP/ }).first().click();
  await expect(page.getByTestId('outbox-code')).toBeVisible();
  await hold('Transfer code appears only in demo mailbox');
  await page.goto(origin + '/qr');
  await page.getByLabel('Amount (VND, optional)').fill('10000');
  await page.getByRole('button', { name: 'Create demo QR', exact: true }).click();
  await expect(page.getByRole('img', { name: 'NovaBank demo receive code' })).toBeVisible();
  await hold('Signed NovaBank QR generated');
  await page.getByLabel('QR text', { exact: true }).fill('https://example.invalid/policy');
  const decoded = page.waitForResponse(r => r.url().endsWith('/api/qr/decode'));
  await page.getByRole('button', { name: 'Read code', exact: true }).click();
  const denied = await decoded;
  expect(denied.status()).toBe(422);
  await writeFile(resolve(out, 'qr-rejection.json'), JSON.stringify({ status: denied.status(), body: await denied.json() }, null, 2));
  await hold('Foreign URL rejected with HTTP 422');
  expect(errors).toEqual([]);
  await page.screenshot({ path: resolve(out, 'qr-rejected.png'), fullPage: true });
  await writeFile(resolve(out, 'ui-recording.json'), JSON.stringify({ passed: true, provider: 'ollama', model_invoked: false, payment_confirmed: false, frames, page_errors: errors }, null, 2));
  console.log('Recorded outbox and QR; no payment confirmed.');
} finally {
  const video = page.video();
  await context.close();
  await video.saveAs(resolve(out, 'outbox-qr.webm'));
  await browser.close();
}
