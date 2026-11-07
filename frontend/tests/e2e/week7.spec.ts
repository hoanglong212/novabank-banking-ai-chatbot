import { test, expect } from '@playwright/test';
import { clearAuthRequestBudget, demoLogin, enterTransactionPin } from './auth-helpers';

test.beforeEach(clearAuthRequestBudget);
test.use({ video: 'on' });

test('Week 7 transfer URLs survive reload and confirm with the transaction PIN', async ({ page }) => {
  await demoLogin(page, 'alice');
  await page.goto('/transfer/new');
  await page.getByLabel('NovaBank account ID').fill('ACC-BOB-001');
  await page.getByRole('textbox', { name: 'Amount', exact: true }).fill('10000');
  const response = page.waitForResponse(r => r.url().endsWith('/api/transfers') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  expect(await (await response).json()).not.toHaveProperty('demo_otp');
  await expect(page).toHaveURL(/\/transfer\/TRF-[^/]+\/review$/);
  await page.reload();
  await page.getByRole('button', { name: 'Continue to verification' }).click();
  await expect(page).toHaveURL(/\/transfer\/TRF-[^/]+\/otp$/);
  await page.reload();
  await enterTransactionPin(page, 'alice');
  await page.getByRole('button', { name: 'Confirm transfer', exact: true }).click();
  await expect(page).toHaveURL(/\/receipt$/);
  await page.reload();
  await expect(page.getByText('Transfer successful', { exact: true })).toBeVisible();
  expect(page.url()).not.toContain('10000');
});

test('Customer cannot open the staff assistant page', async ({ page }) => {
  await demoLogin(page, 'alice');
  await page.goto('/admin/assistant');
  await expect(page.getByRole('alert')).toContainText('403');
});

test('Approval deep link reloads the server proposal and opens separate OTP', async ({ page }) => {
  await demoLogin(page, 'alice');
  const access = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const headers = { Authorization: 'Bearer ' + access };
  const cid = (await (await page.request.post('/api/conversations', { headers, data: { title: 'URL approval' } })).json()).id;
  const grant = await (await page.request.post('/api/agent/runs', { headers,
    data: { conversation_id: cid, content: 'Transfer 10000 VND to ACC-BOB-001.', profile: 'defended' } })).json();
  const delegated = { Authorization: 'Bearer ' + grant.delegated_token };
  const result = await (await page.request.post('/api/agent/tools', { headers: delegated,
    data: { name: 'prepare_transfer', arguments: { to_account: 'ACC-BOB-001', amount_vnd: 10000 } } })).json();
  expect(result.decision).toBe('ALLOW');
  await page.goto('/approvals/' + result.result.approval_id);
  await page.reload();
  await expect(page.getByText('ACC-BOB-001', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Approve proposal', exact: true }).click();
  await expect(page).toHaveURL(/\/transfer\/TRF-[^/]+\/otp$/);
  // Either the PIN field or, for an account without one, the create-PIN step; neither is pre-filled.
  await expect(page.getByLabel('Transaction PIN', { exact: true }).or(page.getByLabel('New 6-digit PIN', { exact: true }))).toHaveValue('');
});

test('New conversation stays selected when an earlier history request finishes', async ({ page }) => {
  await demoLogin(page, 'alice');
  const access = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const headers = { Authorization: 'Bearer ' + access };
  const old = await (await page.request.post('/api/conversations', { headers, data: { title: 'Previous chat' } })).json();
  await page.request.post('/api/conversations/' + old.id + '/messages', { headers, data: { content: 'What is my balance?' } });
  let release!: () => void;
  let seen!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const intercepted = new Promise<void>(resolve => { seen = resolve; });
  await page.route('**/api/conversations', async route => {
    if (route.request().method() !== 'GET') return route.continue();
    seen(); await held;
    await route.fulfill({ json: [old] });
  });
  const history = page.waitForResponse(r => r.url().endsWith('/api/conversations') && r.request().method() === 'GET');
  await page.goto('/assistant');
  await intercepted;
  await page.getByRole('button', { name: 'New conversation', exact: true }).click();
  release(); await (await history).finished();
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await page.getByRole('textbox', { name: 'Message', exact: true }).fill('What is my balance?');
  const created = page.waitForResponse(r => r.url().endsWith('/api/conversations') && r.request().method() === 'POST', { timeout: 5000 });
  await page.getByRole('button', { name: 'Send message', exact: true }).click();
  expect((await (await created).json()).id).not.toBe(old.id);
});
