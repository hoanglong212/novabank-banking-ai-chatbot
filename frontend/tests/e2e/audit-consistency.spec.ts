import { test, expect } from './fixtures';
import { demoLogin, enterTransactionPin } from './auth-helpers';

test('audit: monthly dashboard spending refreshes after a transfer on Home', async ({ page }, info) => {
  await demoLogin(page, 'alice');
  const pulse = page.getByRole('region', { name: 'This month', exact: true });
  await expect(pulse.locator('.rail-flow')).toBeVisible();
  const before = await pulse.locator('.rail-flow').innerText();
  await page.getByRole('button', { name: 'Transfer', exact: true }).click();
  await page.getByLabel('NovaBank account ID').fill('ACC-BOB-001');
  await page.getByRole('textbox', { name: 'Amount', exact: true }).fill('10000');
  await page.getByLabel('Content').fill('Dashboard consistency audit');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Continue to verification' }).click();
  await enterTransactionPin(page, 'alice');
  await page.getByRole('button', { name: 'Confirm transfer', exact: true }).click();
  await expect(page.getByText('Transfer successful', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  const access = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const month = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' }).slice(0, 7);
  const summary = await (await page.request.get(`/api/insights?month=${month}`, { headers: { Authorization: `Bearer ${access}` } })).json();
  await info.attach('authoritative-insights', { body: JSON.stringify({ before, summary }), contentType: 'application/json' });
  await page.screenshot({ path: info.outputPath('home-after-transfer.png'), fullPage: true });
  await expect(pulse.locator('.rail-flow')).toContainText(summary.expense_vnd.toLocaleString('en-US') + ' VND');
});

test('audit: dashboard reports a failed account request with a retry action', async ({ page }) => {
  await page.route('**/api/me', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Audit simulated outage' }) }));
  await demoLogin(page, 'alice');
  await expect(page.getByRole('alert').filter({ hasText: /retry|try again|load|unavailable|outage/i })).toBeVisible();
});

test('audit: monthly spending reports a failed request instead of permanent skeletons', async ({ page }) => {
  await page.route('**/api/insights?**', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Audit simulated outage' }) }));
  await demoLogin(page, 'alice');
  await expect(page.getByRole('region', { name: 'This month', exact: true }).getByRole('alert')).toBeVisible();
});
