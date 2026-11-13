import { test, expect, type Page } from './fixtures';
import { demoLogin, localMessage, transactionCode } from './auth-helpers';

test('SEC-06 stored XSS stays text in customer, Operations and support screens', async ({ page, browser }) => {
  const errors: string[] = [], dialogs: string[] = [];
  const script = '<script>alert(906)</script>', img = '<img src=x onerror=alert(906)>';
  const observe = (p: Page) => {
    p.on('pageerror', e => errors.push(e.message));
    p.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
    p.on('dialog', d => { dialogs.push(d.message()); void d.dismiss(); });
  };
  const inert = async (p: Page) => {
    expect(await p.locator('img[onerror], script:not([src])').count()).toBe(0);
    expect(errors).toEqual([]); expect(dialogs).toEqual([]);
  };
  observe(page);
  await demoLogin(page, 'alice');
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const headers = { Authorization: 'Bearer ' + token };
  const change = await page.request.post('/api/customer/profile/change', { headers, data: { field: 'name', value: script, password: 'Alice@2026' } });
  expect(change.status()).toBe(202);
  const changed = await change.json();
  expect((await page.request.post('/api/actions/confirm', { headers: { ...headers, 'Idempotency-Key': 'SEC06-profile-change' }, data: { challenge_id: changed.challenge_id, code: transactionCode(changed, 'alice@novabank.test', 'ACTION_PROFILE_NAME') } })).ok()).toBeTruthy();
  expect((await page.request.patch('/api/customer/accounts/ACC-ALICE-001', { headers, data: { nickname: img } })).ok()).toBeTruthy();
  const ticket = await page.request.post('/api/support/tickets', { headers, data: { subject: script, description: img } });
  expect(ticket.status()).toBe(201);
  const ticketId = (await ticket.json()).id;
  const draft = await (await page.request.post('/api/transfers', { headers, data: { to_account: 'ACC-BOB-001', amount_vnd: 1000, content: img } })).json();
  const payment = await page.request.post('/api/transfers/' + draft.id + '/confirm', { headers, data: { otp: transactionCode(draft, 'alice@novabank.test', 'TRANSFER_OTP') } });
  expect(payment.ok()).toBeTruthy();
  const tx = (await payment.json()).transaction_id;
  await page.reload();
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await expect(page.locator('dd').filter({ hasText: script })).toBeVisible();
  await inert(page);
  await page.getByRole('button', { name: 'Explore', exact: true }).click();
  await page.getByRole('button', { name: /Accounts & recipients/ }).click();
  await expect(page.getByText(img, { exact: true })).toBeVisible();
  await inert(page);
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: /Help & support/ }).click();
  await page.getByRole('listitem').filter({ hasText: ticketId }).getByRole('button', { name: 'Open ticket' }).click();
  await expect(page.getByRole('dialog')).toContainText(script);
  await expect(page.getByRole('dialog')).toContainText(img);
  await inert(page); await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Activity', exact: true }).click();
  await page.getByRole('searchbox', { name: 'Search', exact: true }).fill(tx);
  // Keep stale day groups visible briefly while the real search request is pending.
  await page.route('**/api/transactions?**', async route => {
    if (new URL(route.request().url()).searchParams.get('q') === tx) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    await route.continue();
  });
  await page.getByRole('button', { name: 'Search transactions', exact: true }).click();
  const matchingTransactions = page.locator('.tx-list .tx');
  await expect(matchingTransactions).toHaveCount(1);
  await expect(matchingTransactions).toContainText(tx);
  await expect(matchingTransactions).toContainText(img);
  await matchingTransactions.click();
  await expect(page.getByRole('dialog')).toContainText(img); await inert(page);

  const ops = await browser.newPage({ baseURL: 'http://127.0.0.1:8092' }); observe(ops);
  await demoLogin(ops, 'operations');
  await ops.getByRole('button', { name: 'Transactions', exact: true }).click();
  await ops.getByRole('searchbox', { name: 'Search', exact: true }).fill(tx);
  await ops.getByRole('button', { name: 'Search transactions', exact: true }).click();
  await expect(ops.locator('tbody')).toContainText(img);
  await ops.getByRole('button', { name: 'View details ' + tx }).click();
  await expect(ops.getByRole('dialog')).toContainText(img); await inert(ops);
  await ops.keyboard.press('Escape');
  await ops.getByRole('button', { name: 'Customers', exact: true }).click();
  await expect(ops.getByText(script + ' · alice', { exact: true })).toBeVisible(); await inert(ops);

  const support = await browser.newPage({ baseURL: 'http://127.0.0.1:8092' }); observe(support);
  await demoLogin(support, 'support');
  await support.getByRole('button', { name: 'Support', exact: true }).click();
  await support.getByRole('listitem').filter({ hasText: ticketId }).getByRole('button', { name: 'Open ticket' }).click();
  await expect(support.getByRole('dialog')).toContainText(script);
  await expect(support.getByRole('dialog')).toContainText(img); await inert(support);
  await ops.close(); await support.close();
});
