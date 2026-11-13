import { DEMO_PIN, enterTransactionPin, transactionCode } from './auth-helpers';
import { test, expect, type Page } from './fixtures';
import { readFileSync } from 'node:fs';
import { demoLogin } from './auth-helpers';

async function login(page: Page, username: string) {
  await demoLogin(page, username);
}

async function credentials(page: Page) {
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  return { Authorization: `Bearer ${token}` };
}

test('Alice–Bob: nine-step banking acceptance with real backend', async ({ page, browser }, info) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page, 'alice');
  await page.getByRole('button', { name: 'Show balance', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Payment account', exact: true })).toContainText('10,000,000 VND');
  await page.getByRole('button', { name: 'Transfer', exact: true }).click();
  await page.getByLabel('NovaBank account ID').fill('ACC-BOB-001');
  await page.getByRole('textbox', { name: 'Amount', exact: true }).fill('2000000');
  await page.getByLabel('Content').fill('Alice Bob acceptance');
  const draftResponse = page.waitForResponse(r => r.url().endsWith('/api/transfers') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  const draft = await (await draftResponse).json();
  const headers = await credentials(page);
  // Preparing a transfer does not move funds.
  expect((await (await page.request.get('/api/me', { headers })).json()).accounts[0].balance_vnd).toBe(10_000_000);
  await expect(page.getByRole('dialog')).toContainText('BOB TRAN');
  await page.getByRole('button', { name: 'Continue to verification' }).click();
  await enterTransactionPin(page, 'alice');
  const completion = page.waitForResponse(r => r.url().endsWith('/confirm') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirm transfer', exact: true }).click();
  const response = await completion;
  const receipt = await response.json();
  const key = response.request().headers()['idempotency-key'];
  expect(key).toBeTruthy();
  await expect(page.getByText('Transfer successful', { exact: true })).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('8,000,000 VND');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PDF receipt' }).click();
  const download = await downloadPromise;
  await download.saveAs(info.outputPath('alice-receipt.pdf'));
  expect(readFileSync(info.outputPath('alice-receipt.pdf')).subarray(0, 5).toString()).toBe('%PDF-');
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  await page.getByRole('button', { name: 'Activity', exact: true }).click();
  await page.getByRole('searchbox', { name: 'Search', exact: true }).fill(receipt.transaction_id);
  await page.getByRole('button', { name: 'Search transactions', exact: true }).click();
  await expect(page.locator('.tx-list .tx')).toHaveCount(1);
  await page.locator('.tx-list .tx').click();
  await expect(page.getByRole('dialog')).toContainText('Balance after transaction');
  await expect(page.getByRole('dialog')).toContainText('8,000,000 VND');
  await page.screenshot({ path: info.outputPath('alice-detail-desktop.png') });
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();

  const bob = await browser.newPage({ baseURL: 'http://127.0.0.1:8092', viewport: { width: 1440, height: 900 } });
  await login(bob, 'bob');
  const bobHeaders = await credentials(bob);
  expect((await (await bob.request.get('/api/me', { headers: bobHeaders })).json()).accounts[0].balance_vnd).toBe(10_750_000);
  await bob.getByRole('button', { name: 'Alerts', exact: true }).click();
  await expect(bob.locator('.notification')).toHaveCount(1);
  await expect(bob.locator('.notification')).toContainText('2,000,000');
  await bob.screenshot({ path: info.outputPath('bob-alert-desktop.png') });
  await bob.getByRole('button', { name: 'View transaction', exact: true }).click();
  await expect(bob.getByRole('dialog')).toContainText('10,750,000 VND');
  const bobRows = await (await bob.request.get('/api/transactions', { headers: bobHeaders })).json();
  const bobTx = bobRows.items.find((t: { transfer_id: string }) => t.transfer_id === draft.id);
  expect(bobTx.direction).toBe('in');
  expect((await bob.request.get(`/api/transactions/${bobTx.id}/receipt.pdf`, { headers: bobHeaders })).ok()).toBeTruthy();
  await bob.keyboard.press('Escape');
  await expect(bob.getByText('0 unread', { exact: true })).toBeVisible();
  await bob.reload();
  await bob.getByRole('button', { name: 'Alerts', exact: true }).click();
  await expect(bob.getByText('0 unread', { exact: true })).toBeVisible();

  const admin = await browser.newPage({ baseURL: 'http://127.0.0.1:8092', viewport: { width: 1440, height: 900 } });
  await login(admin, 'admin');
  await expect(admin.getByRole('heading', { name: 'Operations', exact: true })).toBeVisible();
  await expect(admin.getByRole('button', { name: 'Assistant', exact: true })).toHaveCount(0);
  await admin.getByRole('button', { name: 'Transactions', exact: true }).click();
  await admin.getByRole('searchbox', { name: 'Search', exact: true }).fill(receipt.transaction_id);
  await admin.getByRole('button', { name: 'Search transactions', exact: true }).click();
  await expect(admin.locator('tbody tr')).toHaveCount(1);
  await admin.getByRole('button', { name: `View details ${receipt.transaction_id}` }).click();
  await expect(admin.getByText('TRANSFER COMPLETED', { exact: true })).toBeVisible();
  await expect(admin.getByRole('dialog')).toContainText('8,000,000');
  await admin.screenshot({ path: info.outputPath('admin-audit-desktop.png') });

  // Retry the successful confirmation with the exact same request key.
  const replay = await page.request.post(`/api/transfers/${draft.id}/confirm`, {
    headers: { ...headers, 'Idempotency-Key': key }, data: { otp: DEMO_PIN },
  });
  expect(replay.status()).toBe(200);
  expect((await replay.json()).transaction_id).toBe(receipt.transaction_id);
  const rejected = await page.request.post('/api/transfers', { headers, data: { to_bank: 'NovaBank', to_account: 'ACC-BOB-001', amount_vnd: 20_000_000 } });
  expect(rejected.status()).toBe(400);
  expect((await (await page.request.get('/api/me', { headers })).json()).accounts[0].balance_vnd).toBe(8_000_000);
  expect((await (await bob.request.get('/api/notifications', { headers: bobHeaders })).json()).total).toBe(1);

  const charlie = await browser.newPage({ baseURL: 'http://127.0.0.1:8092' });
  await login(charlie, 'charlie');
  const third = await credentials(charlie);
  for (const id of [receipt.transaction_id, bobTx.id]) {
    expect((await charlie.request.get(`/api/transactions/${id}`, { headers: third })).status()).toBe(404);
    expect((await charlie.request.get(`/api/transactions/${id}/receipt.pdf`, { headers: third })).status()).toBe(404);
  }
  expect((await charlie.request.get('/api/admin/transactions', { headers: third })).status()).toBe(403);
  expect((await (await charlie.request.get('/api/transactions', { headers: third })).json()).total).toBe(0);
  expect(errors).toEqual([]);
  await Promise.all([bob.close(), admin.close(), charlie.close()]);
});

for (const viewport of [{ width: 375, height: 812 }, { width: 768, height: 1024 }]) {
  test(`history and alerts usable at ${viewport.width}px`, async ({ page }, info) => {
    await page.setViewportSize(viewport);
    await login(page, 'alice');
    // Arrange this test's own completed transfer instead of relying on another test.
    const headers = await credentials(page);
    const draftResponse = await page.request.post('/api/transfers', { headers,
      data: { to_account: 'ACC-BOB-001', amount_vnd: 2000, content: 'Responsive receipt' } });
    expect(draftResponse.ok()).toBeTruthy();
    const draft = await draftResponse.json();
    const confirmed = await page.request.post(`/api/transfers/${draft.id}/confirm`, {
      headers: { ...headers, 'Idempotency-Key': `responsive-${viewport.width}` },
      data: { otp: transactionCode(draft, 'alice@novabank.test', 'TRANSFER_OTP') },
    });
    expect(confirmed.ok()).toBeTruthy();
    const receipt = await confirmed.json();
    await page.getByRole('button', { name: 'Activity', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Search transactions', exact: true })).toBeEnabled();
    await page.getByRole('searchbox', { name: 'Search', exact: true }).fill(receipt.transaction_id);
    await page.getByRole('button', { name: 'Search transactions', exact: true }).click();
    await expect(page.locator('.tx-list .tx')).toHaveCount(1);
    const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
    await page.screenshot({ path: info.outputPath('activity.png'), fullPage: true });
    await page.locator('.tx-list .tx').first().click();
    await expect(page.getByRole('button', { name: 'Download PDF receipt' })).toBeVisible();
    await page.screenshot({ path: info.outputPath('receipt.png') });
    await page.keyboard.press('Escape');
    // Phones reach Alerts through the bell on Home; wider screens through the sidebar.
    await page.getByRole('button', { name: 'Home', exact: true }).click();
    await page.getByRole('button', { name: /^Notifications/ }).click();
    await expect(page.getByRole('heading', { name: 'Alerts', exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath('alerts.png'), fullPage: true });
  });
}
