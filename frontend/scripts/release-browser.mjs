import { chromium, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve('..'), out = resolve(root, '.local/full-roadmap/ui-qa');
const python = resolve(root, 'backend/.venv/Scripts/python.exe');
const db = resolve(root, '.local/full-roadmap/rich-demo.sqlite3');
const baseURL = process.env.DEMO_URL || 'http://127.0.0.1:8084';
mkdirSync(out, { recursive: true });
const browser = await chromium.launch(); const report = { screenshots: [], errors: [], checks: [] };
function code(user, kind = 'LOGIN_OTP') {
  return execFileSync(python, ['-c', 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute("SELECT secret_text FROM dev_outbox WHERE user_id=? AND kind=? AND secret_text IS NOT NULL ORDER BY rowid DESC LIMIT 1",(sys.argv[2],sys.argv[3])).fetchone()[0])', db, user, kind], { encoding: 'utf8' }).trim();
}
async function login(page, user) {
  await page.goto(baseURL); await page.getByLabel('Username', { exact: true }).fill(user);
  await page.getByLabel('Password', { exact: true }).fill(user[0].toUpperCase() + user.slice(1) + '@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
  await page.getByLabel('Verification code', { exact: true }).fill(code(user));
  await page.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
}
async function snap(page, name, width) {
  await page.waitForTimeout(350);
  const layout = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
    unlabeled: [...document.querySelectorAll('input,select,textarea')].filter(e => e.getClientRects().length && !['hidden','submit','button'].includes(e.type) && !e.labels?.length && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby')).map(e => e.outerHTML.slice(0,100)) }));
  const file = `${width}-${name}.png`; await page.screenshot({ path: resolve(out, file), fullPage: true });
  report.screenshots.push({ file, ...layout });
  if (layout.scroll > width || layout.unlabeled.length) report.errors.push({ name, width, layout });
}
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on('pageerror', e => report.errors.push({ pageerror: e.message }));
  await login(page, 'alice');
  const nav = page.getByRole('navigation', { name: 'Main', exact: true });
  const sections = ['Accounts & recipients','Cards Manage','Pay bills','Savings Build','Spending & budgets','Goals & calculator','Statements Download','Demo QR Receive','Help & support'];
  for (const width of [1440, 768, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await nav.getByRole('button', { name: 'Home', exact: true }).click(); await snap(page, 'home', width);
    await nav.getByRole('button', { name: 'Explore', exact: true }).click(); await snap(page, 'explore', width);
    for (const [i, name] of sections.entries()) {
      await page.getByRole('button', { name, exact: false }).click();
      await snap(page, `service-${i}`, width);
      await page.getByRole('button', { name: 'All services', exact: true }).click();
    }
    await nav.getByRole('button', { name: 'Profile', exact: true }).click(); await snap(page, 'profile', width);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await nav.getByRole('button', { name: 'Assistant', exact: true }).click();
  await page.getByRole('button', { name: 'New conversation', exact: true }).click();
  await page.getByRole('textbox', { name: /message|ask/i }).fill('Transfer 200000 VND to ACC-BOB-001 content browser');
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Review and approve', exact: true })).toBeVisible({ timeout: 150000 });
  await expect(page.getByText('No payment or card change has been made by the assistant.', { exact: false })).toBeVisible();
  await snap(page, 'agent-proposal', 1440);
  await page.getByRole('button', { name: 'Review and approve', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible(); await snap(page, 'agent-transfer-review', 1440);
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).not.toBeVisible();
  report.checks.push('Real Ollama SSE proposal and approval open transfer review; Escape closes and restores focus.');
  const admin = await context.newPage(); await login(admin, 'admin');
  for (const name of ['Overview','Customers','Settings','Knowledge','Research','Audit']) {
    await admin.getByRole('button', { name, exact: true }).click(); await snap(admin, 'admin-' + name, 1440);
  }
  await context.close();
} catch (error) {
  report.errors.push({ fatal: error.message }); process.exitCode = 1;
} finally {
  await browser.close(); writeFileSync(resolve(out, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ screenshots: report.screenshots.length, errors: report.errors, checks: report.checks }, null, 2));
}
