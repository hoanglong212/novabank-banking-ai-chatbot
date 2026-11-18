import { test, expect } from './fixtures';
import { authenticatorCode, createTransactionPin, demoLogin, localMessage } from './auth-helpers';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pythonExecutable } from './python';

test('fresh TOTP login, recipient-bound step-up and separate email OTP protect a new payee', async ({ page, browser }, info) => {
  test.setTimeout(120_000);
  await demoLogin(page, 'alice');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Profile', exact: true }).click();
  await page.getByRole('button', { name: 'Set up authenticator', exact: true }).click();
  await page.getByLabel('Current password', { exact: true }).fill('Alice@2026');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  const secret = await page.getByLabel('Setup key', { exact: true }).inputValue();
  await page.getByLabel('Authenticator code', { exact: true }).fill(authenticatorCode(secret, -1));
  await page.getByRole('button', { name: 'Enable authenticator', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Sign-in verification', exact: true })).toContainText('Authenticator enabled');

  const context = await browser.newContext({ baseURL: 'http://127.0.0.1:8092', viewport: { width: 1440, height: 900 } });
  const customer = await context.newPage();
  try {
    await customer.goto('/');
    await customer.getByLabel('Username', { exact: true }).fill('alice');
    await customer.getByLabel('Password', { exact: true }).fill('Alice@2026');
    await customer.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(customer.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
    await customer.screenshot({ path: info.outputPath('01-login-totp.png'), fullPage: true });
    await customer.getByLabel('Verification code', { exact: true }).fill(authenticatorCode(secret));
    await customer.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
    await expect(customer.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
    const access = await customer.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
    const headers = { Authorization: 'Bearer ' + access };
    const before = (await (await customer.request.get('/api/me', { headers })).json()).accounts[0].balance_vnd;
    const mailsBefore = (await (await customer.request.get('/api/dev/outbox', { headers })).json()).items.filter((item: { kind: string }) => item.kind === 'TRANSFER_OTP').length;

    // Explicit fresh-payee fixture: never alter the active demonstration DB.
    const root = resolve('..');
    const db = JSON.parse(readFileSync(resolve(root, '.local/e2e/latest.json'), 'utf8')).db_path;
    execFileSync(pythonExecutable(root), ['-c',
      'import pathlib,sqlite3,sys; p=pathlib.Path(sys.argv[1]).resolve(); root=pathlib.Path(sys.argv[2]).resolve(); assert p.is_relative_to(root/".local"/"e2e"); c=sqlite3.connect(p); exists=c.execute("SELECT 1 FROM sqlite_master WHERE type=\'table\' AND name=\'verified_payees\'").fetchone(); c.execute("DELETE FROM verified_payees WHERE owner_id=? AND to_account=?",("alice","ACC-CHARLIE-001")) if exists else None; c.commit(); assert c.execute("SELECT COUNT(*) FROM transfers WHERE owner_id=? AND to_account=? AND status=\'COMPLETED\'",("alice","ACC-CHARLIE-001")).fetchone()[0]==0', db, root]);

    await customer.getByRole('button', { name: 'Transfer', exact: true }).click();
    await customer.getByLabel('NovaBank account ID').fill('ACC-CHARLIE-001');
    await customer.getByRole('textbox', { name: 'Amount', exact: true }).fill('10000');
    await customer.getByLabel('Content').fill('New recipient MFA evidence');
    const created = customer.waitForResponse(r => r.url().endsWith('/api/transfers') && r.request().method() === 'POST');
    await customer.getByRole('button', { name: 'Continue', exact: true }).click();
    const draft = await (await created).json();
    expect(draft.id).toBeTruthy();
    expect((await (await customer.request.get('/api/dev/outbox', { headers })).json()).items.filter((item: { kind: string }) => item.kind === 'TRANSFER_OTP').length).toBe(mailsBefore);
    const premature = await customer.request.post(`/api/transfers/${draft.id}/otp`, { headers });
    expect(premature.status()).toBe(400);
    expect((await premature.json()).detail).toBe('STEP_UP_REQUIRED');
    await customer.getByRole('button', { name: 'Continue to verification', exact: true }).click();
    await expect(customer.getByRole('heading', { name: 'Verify this new recipient', exact: true })).toBeVisible();
    await customer.screenshot({ path: info.outputPath('02-recipient-stepup.png'), fullPage: true });
    await customer.getByLabel('New-recipient authenticator code', { exact: true }).fill(authenticatorCode(secret, 1));
    await customer.getByRole('button', { name: 'Verify new recipient', exact: true }).click();
    await expect(customer.getByRole('heading', { name: 'Create your transaction PIN', exact: true })).toBeVisible();
    await createTransactionPin(customer, 'alice');
    await expect(customer.getByRole('button', { name: 'Request transfer verification code', exact: true })).toBeVisible();
    await customer.screenshot({ path: info.outputPath('03-stepup-passed.png'), fullPage: true });
    expect((await (await customer.request.get('/api/me', { headers })).json()).accounts[0].balance_vnd).toBe(before);
    await customer.getByRole('button', { name: 'Request transfer verification code', exact: true }).click();
    await expect(customer.getByLabel('Transfer email code', { exact: true })).toBeVisible();
    await customer.screenshot({ path: info.outputPath('04-separate-email-otp.png'), fullPage: true });
    await customer.getByLabel('Transfer email code', { exact: true }).fill(localMessage('alice@novabank.test', 'TRANSFER_OTP').code);
    await customer.getByRole('button', { name: 'Confirm transfer', exact: true }).click();
    await expect(customer.getByText('Transfer successful', { exact: true })).toBeVisible();
    expect((await (await customer.request.get('/api/me', { headers })).json()).accounts[0].balance_vnd).toBe(before - 10000);
    await customer.screenshot({ path: info.outputPath('05-confirmed-receipt.png'), fullPage: true });
  } finally {
    await context.close();
  }
});
