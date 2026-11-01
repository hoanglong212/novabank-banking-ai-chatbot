import { test, expect } from '@playwright/test';
import { demoLogin } from './auth-helpers';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve, relative } from 'node:path';

test.afterEach(() => {
  // This suite shares one disposable server. Do not consume the next test's IP login budget.
  // Rate limits themselves are exercised without resets in backend/tests/test_TRF_14.py and identity tests.
  const root = resolve('..');
  const db = resolve(JSON.parse(readFileSync(resolve(root, '.local/e2e/latest.json'), 'utf8')).db_path);
  if (relative(resolve(root, '.local/e2e'), db).startsWith('..')) throw new Error('Expected disposable E2E database');
  execFileSync(resolve(root, 'backend/.venv/Scripts/python.exe'), ['-c',
    "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"DELETE FROM identity_limits WHERE scope LIKE 'request:/api/auth/%'\"); c.commit(); c.close()", db]);
});

test('DSH-01 balance visibility survives reload and total includes all accounts', async ({ page }) => {
  await page.route('**/api/me', async route => {
    const response = await route.fetch();
    const body = await response.json();
    if (body.accounts?.length) body.accounts.push({ ...body.accounts[0], id: 'ACC-SECOND', balance_vnd: 123456 });
    await route.fulfill({ response, json: body });
  });
  await demoLogin(page, 'charlie');
  const card = page.getByRole('region', { name: 'Payment account', exact: true });
  await page.getByRole('button', { name: 'Show balance', exact: true }).click();
  const total = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const me = await (await page.request.get('/api/me', { headers: { Authorization: 'Bearer ' + total } })).json();
  const expected = (me.accounts.reduce((n: number, a: { balance_vnd: number }) => n + a.balance_vnd, 0) + 123456).toLocaleString('en-US') + ' VND';
  await expect(card).toContainText(expected);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Hide balance', exact: true })).toBeVisible();
  await expect(card).toContainText(expected);
  await page.getByRole('button', { name: 'Hide balance', exact: true }).click();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Show balance', exact: true })).toBeVisible();
});

test('BEN-01 edit and search saved recipients through the UI', async ({ page }) => {
  await demoLogin(page, 'charlie');
  await page.getByRole('button', { name: 'Explore', exact: true }).click();
  await page.getByRole('button', { name: /Accounts & recipients/ }).click();
  await page.getByLabel('Account ID or number').fill('ACC-BOB-001');
  await page.getByLabel('Nickname', { exact: true }).fill('Family test');
  await page.getByRole('button', { name: 'Verify and save recipient' }).click();
  const row = page.getByRole('listitem').filter({ hasText: 'Family test' });
  await row.getByRole('button', { name: 'Edit nickname' }).click();
  await row.getByLabel('Recipient nickname').fill('Rent test');
  await row.getByRole('button', { name: 'Save nickname' }).click();
  await page.getByLabel('Search saved recipients').fill('no match');
  await expect(page.getByText('Rent test', { exact: true })).toHaveCount(0);
  await page.getByLabel('Search saved recipients').fill('Rent');
  await expect(page.getByText('Rent test', { exact: true })).toBeVisible();
  await page.getByRole('listitem').filter({ hasText: 'Rent test' }).getByRole('button', { name: 'Remove' }).click();
});

test('AI-12 displays live text and Stop cancels the real bank run', async ({ page }) => {
  await page.route('**/api/health', async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), agent_mode: 'service' } });
  });
  // Replace only the slow model transport. Run creation/cancellation use the actual bank API.
  await page.addInitScript(() => {
    const original = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const path = String(input);
      if (!path.endsWith('/stream')) return original(input, init);
      const conversation = path.split('/')[3];
      const grant = await (await original('/api/agent/runs', { method: 'POST', headers: init?.headers,
        body: JSON.stringify({ conversation_id: conversation, ...JSON.parse(String(init?.body)) }) })).json();
      const encode = (event: string, data: unknown) => new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
      const body = new ReadableStream({ start(controller) {
        controller.enqueue(encode('run', { run_id: grant.run_id }));
        controller.enqueue(encode('text', { text: 'Live verified response.' }));
        init?.signal?.addEventListener('abort', () => controller.error(new DOMException('Cancelled', 'AbortError')), { once: true });
      } });
      return new Response(body, { headers: { 'Content-Type': 'text/event-stream' } });
    };
  });
  await demoLogin(page, 'charlie');
  await page.getByRole('button', { name: 'Assistant', exact: true }).click();
  await page.getByRole('textbox', { name: 'Message', exact: true }).fill('What is my balance?');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.getByText('Live verified response.', { exact: true })).toBeVisible();
  const cancellation = page.waitForResponse(r => r.url().endsWith('/cancel'));
  await page.getByRole('button', { name: 'Stop response', exact: true }).click();
  expect((await (await cancellation).json()).status).toBe('CANCELLED');
  await expect(page.getByRole('textbox', { name: 'Message', exact: true })).toBeEnabled();
  await expect(page.getByText('Live verified response.', { exact: true })).toHaveCount(0);
});
