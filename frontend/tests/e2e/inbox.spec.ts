import { enterTransactionPin } from './auth-helpers';
import { test, expect } from './fixtures';

// R1 fix, end to end: sign in through the challenge-bound inbox tab, read only own mail, then pay with confirmation.
test('sign in via the demo inbox tab, read own mail only, then confirm a transfer', async ({ page, context, browser }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  // Bob has a live sign-in code in the outbox throughout; Alice must never see it.
  expect((await page.request.post('/api/auth/login', { data: { username: 'bob', password: 'Bob@2026' } })).status()).toBe(202);

  await page.goto('/');
  await page.getByLabel('Username', { exact: true }).fill('alice');
  await page.getByLabel('Password', { exact: true }).fill('Alice@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();

  const [loginInbox] = await Promise.all([context.waitForEvent('page'), page.getByRole('button', { name: 'local demo inbox', exact: true }).click()]);
  const code = (await loginInbox.getByTestId('outbox-code').textContent())!.trim();
  expect(code).toMatch(/^\d{6}$/);
  // The challenge is kept in memory only, not in the address bar or history.
  expect(new URL(loginInbox.url()).hash).toBe('');
  await expect(loginInbox.getByRole('list', { name: 'Messages' }).getByRole('listitem')).toHaveCount(1);
  await loginInbox.close();

  await page.getByLabel('Verification code', { exact: true }).fill(code);
  await page.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(page.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();

  // Signed in: an inbox tab opened from the app borrows this tab's token and lists Alice's mail only.
  const [ownInbox] = await Promise.all([context.waitForEvent('page'), page.evaluate(() => { window.open('/outbox'); })]);
  const recipients = ownInbox.getByRole('list', { name: 'Messages' }).locator('small');
  await expect(recipients.first()).toBeVisible();
  for (const text of await recipients.allTextContents()) expect(text).toMatch(/^a\*\*\*@\*\*\*/);
  // Its copied session was dropped, so this tab cannot later reuse (and revoke) Alice's refresh token.
  expect(await ownInbox.evaluate(() => sessionStorage.getItem('novabank-session'))).toBeNull();
  await ownInbox.close();

  // The main tab's session is intact: pay Bob and confirm.
  await page.getByRole('button', { name: 'Transfer', exact: true }).click();
  await page.getByLabel('NovaBank account ID').fill('ACC-BOB-001');
  await page.getByRole('textbox', { name: 'Amount', exact: true }).fill('50000');
  await page.getByLabel('Content').fill('Inbox e2e');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('BOB TRAN');
  await page.getByRole('button', { name: 'Continue to verification' }).click();
  await enterTransactionPin(page, 'alice');
  const completion = page.waitForResponse(r => r.url().endsWith('/confirm') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirm transfer', exact: true }).click();
  expect((await completion).status()).toBe(200);
  await expect(page.getByText('Transfer successful', { exact: true })).toBeVisible();

  // A stranger's browser sees nothing: no session, no challenge.
  const stranger = await browser.newContext();
  const anonymous = await stranger.newPage();
  await anonymous.goto('/outbox');
  await expect(anonymous.getByRole('alert')).toContainText('Open the demo inbox from NovaBank');
  expect((await anonymous.request.get('/api/dev/outbox')).status()).toBe(401);
  await stranger.close();
  expect(errors).toEqual([]);
});
