import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const origin = process.env.NOVABANK_URL || 'http://127.0.0.1:8081';
const out = resolve('../.local/week7-deploy');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const { user, prompt, tool, label } of [
    { user: 'alice', prompt: 'What is my balance?', tool: 'get_account_balance', label: 'alice-assistant' },
    { user: 'admin', prompt: 'How many users are registered?', tool: 'get_user_count', label: 'admin-assistant' },
    { user: 'alice', prompt: 'Show my savings and interest rates.', tool: 'get_savings', label: 'alice-savings' },
  ]) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
      recordVideo: { dir: resolve(out, 'videos'), size: { width: 1440, height: 1000 } } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin);
    await page.getByLabel('Username', { exact: true }).fill(user);
    await page.getByLabel('Password', { exact: true }).fill(user[0].toUpperCase() + user.slice(1) + '@2026');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Verify sign-in' })).toBeVisible();
    const rows = await (await page.request.get(origin + '/api/dev/outbox')).json();
    const mail = rows.items.find(row => row.kind === 'LOGIN_OTP');
    const detail = await (await page.request.get(origin + '/api/dev/outbox/' + mail.id)).json();
    await page.getByLabel('Verification code', { exact: true }).fill(detail.code);
    await page.getByRole('button', { name: 'Verify and sign in' }).click();
    await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
    await page.goto(origin + (user === 'admin' ? '/admin/assistant' : '/assistant'));
    await page.getByRole('button', { name: 'New conversation', exact: true }).click();
    await page.getByRole('textbox', { name: 'Message', exact: true }).fill(prompt);
    const streamed = page.waitForResponse(r => r.url().endsWith('/stream') && r.request().method() === 'POST', { timeout: 150000 });
    await page.getByRole('button', { name: 'Send message' }).click();
    const response = await streamed;
    expect(response.ok()).toBeTruthy();
    const conversationId = response.url().split('/conversations/')[1].split('/')[0];
    const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')).token);
    const headers = { Authorization: 'Bearer ' + token };
    let run;
    await expect.poll(async () => {
      const list = await (await page.request.get(origin + '/api/agent/runs?conversation_id=' + conversationId, { headers })).json();
      if (!list.items?.length) return 'PENDING';
      run = await (await page.request.get(origin + '/api/agent/runs/' + list.items[0].id, { headers })).json();
      return run.status;
    }, { timeout: 180000, intervals: [1000, 2000] }).toBe('COMPLETED');
    expect(run.status).toBe('COMPLETED');
    expect(run.tool_calls.some(call => call.name === tool && call.decision === 'ALLOW')).toBeTruthy();
    await page.screenshot({ path: resolve(out, label + '.png'), fullPage: true });
    expect(errors).toEqual([]);
    const health = await (await page.request.get(origin + '/api/health')).json();
    results.push({ user, origin, prompt, tool, login: 'passed', assistant: 'passed', provider: health.llm_provider, model: run.model, input_tokens: run.input_tokens, output_tokens: run.output_tokens, page_errors: errors });
    const video = page.video();
    await context.close();
    await video.saveAs(resolve(out, label + '.webm'));
  }
  await writeFile(resolve(out, 'browser-check.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results));
} finally { await browser.close(); }
