import { test, expect, type Page } from './fixtures';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import { demoLogin, localMessage, transactionCode } from './auth-helpers';

async function headers(page: Page) {
  return { Authorization: 'Bearer ' + await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token) };
}
async function transfer(page: Page, bank: string, account: string, amount: number) {
  const auth = await headers(page);
  const draft = await page.request.post('/api/transfers', { headers: auth, data: { to_bank: bank, to_account: account, amount_vnd: amount, content: 'Admin dashboard acceptance' } });
  expect(draft.status()).toBe(201);
  const body = await draft.json();
  const id = body.id;
  const result = await page.request.post(`/api/transfers/${id}/confirm`, { headers: auth, data: { otp: transactionCode(body, 'alice@novabank.test', 'TRANSFER_OTP') } });
  expect(result.ok()).toBeTruthy();
  return id as string;
}
function settlementFixture(pendingId?: string) {
  const root = resolve('..');
  const db = resolve(JSON.parse(readFileSync(resolve(root, '.local/e2e/latest.json'), 'utf8')).db_path);
  if (relative(resolve(root, '.local/e2e'), db).startsWith('..')) throw new Error('Expected disposable E2E database');
  const venv = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
  const python = process.env.NOVABANK_PYTHON || (existsSync(venv) ? venv : 'python');
  // Keep only this fixture pending while the normal worker can continue processing other transfers.
  const code = pendingId
    ? "import sqlite3,sys; from datetime import datetime,timedelta,timezone; c=sqlite3.connect(sys.argv[2]); c.execute(\"UPDATE interbank_settlements SET due_at=? WHERE transfer_id=? AND status='PENDING'\", ((datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),sys.argv[3])); c.commit(); c.close()"
    : "import sys; sys.path.insert(0,sys.argv[1]); from app.database import Database; from app.settlement import process_due; process_due(Database(sys.argv[2]),force=True)";
  execFileSync(python, ['-c', code, resolve(root, 'backend'), db, ...(pendingId ? [pendingId] : [])]);
}

test('admin empty overview, period filter, queues, and read-only auditor', async ({ page, browser }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await demoLogin(page, 'admin');
  await expect(page.getByRole('heading', { name: 'Operations', exact: true })).toBeVisible();
  await expect(page.getByText('No settled transfers in this period', { exact: true })).toBeVisible();
  // The real maintenance worker reconciles the seeded ledger at startup.
  await expect(page.getByText('Ledger balanced', { exact: true })).toBeVisible();
  const response = page.waitForResponse(r => r.url().includes('/admin/overview?days=30'));
  await page.getByRole('button', { name: '30 days', exact: true }).click();
  expect((await (await response).json()).dashboard.daily).toHaveLength(30);
  await page.getByRole('button', { name: /Pending settlements Current queue/ }).click();
  await expect(page.getByRole('dialog', { name: 'Pending settlements', exact: true })).toContainText('No transfers in this queue');
  await page.keyboard.press('Escape');
  await page.screenshot({ path: '../.local/admin-home/empty-desktop.png', animations: 'disabled' });
  const context = await browser.newContext(); const auditor = await context.newPage();
  await demoLogin(auditor, 'auditor');
  await expect(auditor.getByText('Read-only access.', { exact: false })).toBeVisible();
  await expect(auditor.getByRole('button', { name: 'Run reconciliation', exact: true })).toHaveCount(0);
  await context.close();
});

test('real transfer outcomes, drilldowns, reconciliation and responsive admin home', async ({ page, browser }) => {
  const context = await browser.newContext(); const customer = await context.newPage();
  await demoLogin(customer, 'alice');
  const completed = await transfer(customer, 'NovaBank', 'ACC-BOB-001', 325000);
  const failed = await transfer(customer, 'Demo Bank A', '1234560000', 75000);
  settlementFixture();
  const pending = await transfer(customer, 'Demo Bank A', '1234567890', 250000);
  settlementFixture(pending);
  await customer.request.post('/api/support/tickets', { headers: await headers(customer), data: { subject: 'Transfer follow-up', description: 'Please review the simulated transfer.' } });
  await context.close();
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await demoLogin(page, 'admin');
  const metrics = page.locator('.admin-metric');
  await expect(metrics.filter({ hasText: 'Settled transfer volume' })).toContainText('325,000 VND');
  await expect(metrics.filter({ hasText: 'Completion rate' })).toContainText('50%');
  await expect(metrics.filter({ hasText: 'Awaiting settlement' }).locator('strong')).toHaveText('1');
  await page.getByRole('button', { name: `Review transfer ${completed}`, exact: true }).click();
  const review = page.getByRole('dialog', { name: 'Transfer review', exact: true });
  await expect(review).toContainText('325,000 VND');
  await expect(review).toContainText('TRANSFER COMPLETED');
  await page.screenshot({ path: '../.local/admin-home/transfer-review.png', animations: 'disabled' });
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: /Failed transfers Within/ }).click();
  await page.getByRole('dialog', { name: 'Failed transfers', exact: true }).getByRole('button', { name: `Review transfer ${failed}`, exact: true }).click();
  await expect(review.locator('.form-error')).not.toBeEmpty();
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  await page.getByRole('button', { name: /Pending settlements Current/ }).click();
  await expect(page.getByRole('dialog', { name: 'Pending settlements', exact: true }).getByRole('button', { name: `Review transfer ${pending}` })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Run reconciliation', exact: true }).click();
  await expect(page.getByText('Ledger balanced', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'View report', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Reconciliation report', exact: true })).toContainText('0 VND');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '90 days', exact: true }).click();
  await expect(page.locator('.admin-chart-bar')).toHaveCount(90);
  await page.getByRole('button', { name: '7 days', exact: true }).click();
  await expect(page.locator('.admin-chart-bar')).toHaveCount(7);
  for (const width of [1440, 768, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 });
    await page.locator('#main').evaluate(el => { el.scrollTop = 0; });
    await page.screenshot({ path: `../.local/admin-home/overview-${width}.png`, animations: 'disabled' });
    await page.locator('.admin-volume').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `../.local/admin-home/chart-${width}.png`, animations: 'disabled' });
    await page.locator('.admin-recent').scrollIntoViewIfNeeded();
    await page.screenshot({ path: `../.local/admin-home/activity-${width}.png`, animations: 'disabled' });
    await page.locator('#main').evaluate(el => { el.scrollTop = el.scrollHeight; });
    await page.screenshot({ path: `../.local/admin-home/footer-${width}.png`, animations: 'disabled' });
    const layout = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
      overflow: [...document.querySelectorAll('body *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1).slice(0, 15).map(el => ({ tag: el.tagName, className: el.className, right: el.getBoundingClientRect().right })) }));
    expect(layout.scroll, JSON.stringify(layout)).toBeLessThanOrEqual(layout.width);
  }
  await page.getByRole('button', { name: `Review transfer ${pending}`, exact: true }).click();
  await expect(review).toContainText('To 1234567890');
  await page.screenshot({ path: '../.local/admin-home/review-mobile.png', animations: 'disabled' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'All transactions', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Transactions table', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Overview', exact: true }).click();
  await page.getByRole('button', { name: /Customer verification Active customers/ }).click();
  await expect(page.getByRole('heading', { name: 'Customers and staff', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Overview', exact: true }).click();
  await page.getByRole('button', { name: /Open support requests Open and in progress/ }).click();
  await expect(page.getByText('Transfer follow-up', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('dashboard request failure is actionable and retry restores real data', async ({ page }) => {
  let fail = true;
  await page.route('**/api/admin/overview*', route => fail ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Dashboard temporarily unavailable.' }) }) : route.continue());
  await demoLogin(page, 'admin');
  await expect(page.getByRole('alert')).toContainText('Dashboard temporarily unavailable');
  fail = false;
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.locator('.admin-metrics')).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
