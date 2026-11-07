import { test, expect, type Page } from '@playwright/test';
import { completeEmailMfa, demoLogin, enterTransactionPin, localMessage } from './auth-helpers';

const password = 'A long browser passphrase 2026!';
const replacement = 'A different browser passphrase 2026!';
test.use({ actionTimeout: 10_000 });

function outbox(email: string, kind: string) {
  return localMessage(email, kind).action_url as string;
}

async function signIn(page: Page, name: string, secret: string) {
  await page.getByLabel('Username', { exact: true }).fill(name);
  await page.getByLabel('Password', { exact: true }).fill(secret);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await completeEmailMfa(page, name + '@example.test');
}

test('register, verify, recover and revoke previous sessions through the real UI', async ({ page, browser }, info) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/vietqr/banks', route => route.fulfill({ json: [] }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Create an account', exact: true }).click();
  await page.getByLabel('Display name', { exact: true }).fill('Đặng An');
  await page.getByLabel('Username', { exact: true }).fill('browser_dana');
  await page.getByLabel('Email', { exact: true }).fill('browser_dana@example.test');
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Confirm password', { exact: true }).fill('Different password');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Passwords do not match');
  await page.getByLabel('Confirm password', { exact: true }).fill(password);
  await page.screenshot({ path: info.outputPath('register-desktop.png'), fullPage: true });
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('local demo inbox');
  const verifyUrl = outbox('browser_dana@example.test', 'VERIFY_EMAIL');
  await page.goto(verifyUrl);
  await expect(page).toHaveURL('http://127.0.0.1:8092/');
  await page.getByRole('button', { name: 'Verify email', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Email verified');
  await signIn(page, 'browser_dana', password);
  // New accounts must create a transaction PIN before banking.
  await expect(page.getByRole('heading', { name: 'Create your transaction PIN', exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath('pin-gate.png'), fullPage: true });
  await page.getByLabel('Current password', { exact: true }).fill(password);
  await page.getByLabel('New 6-digit PIN', { exact: true }).fill('482916');
  await page.getByLabel('Repeat PIN', { exact: true }).fill('482916');
  await page.getByRole('button', { name: 'Create PIN and start banking', exact: true }).click();
  await page.getByRole('button', { name: 'Show balance', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Payment account' })).toContainText('0 VND');
  const old = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const own = await (await page.request.get('/api/me', { headers: { Authorization: `Bearer ${old}` } })).json();
  const payer = await browser.newPage({ baseURL: 'http://127.0.0.1:8092' });
  await demoLogin(payer, 'alice');
  await payer.getByRole('button', { name: 'Transfer', exact: true }).click();
  await payer.getByLabel('NovaBank account ID').fill(own.accounts[0].id);
  await payer.getByRole('textbox', { name: 'Amount', exact: true }).fill('100000');
  const prepared = payer.waitForResponse(response => response.url().endsWith('/api/transfers') && response.request().method() === 'POST');
  await payer.getByRole('button', { name: 'Continue', exact: true }).click();
  await prepared;
  await payer.getByRole('button', { name: 'Continue to verification' }).click();
  await enterTransactionPin(payer, 'alice');
  await payer.getByRole('button', { name: 'Confirm transfer', exact: true }).click();
  await expect(payer.getByText('Transfer successful', { exact: true })).toBeVisible();
  await payer.close();
  await page.getByRole('button', { name: 'Alerts', exact: true }).click();
  await expect(page.locator('.notification')).toContainText('100,000');
  await page.getByRole('button', { name: 'Home', exact: true }).click();
  // DSH-01 now retains the visibility chosen earlier in this same test.
  await expect(page.getByRole('button', { name: 'Hide balance', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Payment account' })).toContainText('100,000 VND');

  const recovery = await browser.newPage({ baseURL: 'http://127.0.0.1:8092', viewport: { width: 375, height: 812 } });
  await recovery.route('**/api/vietqr/banks', route => route.fulfill({ json: [] }));
  await recovery.goto('/');
  await recovery.getByRole('button', { name: 'Forgot password?', exact: true }).click();
  await recovery.getByLabel('Email', { exact: true }).fill('browser_dana@example.test');
  await recovery.getByRole('button', { name: 'Send reset link', exact: true }).click();
  await expect(recovery.getByRole('status')).toContainText('local demo inbox');
  await recovery.goto(outbox('browser_dana@example.test', 'RESET_PASSWORD'));
  await expect(recovery).toHaveURL('http://127.0.0.1:8092/');
  await recovery.getByLabel('New password', { exact: true }).fill(replacement);
  await recovery.getByLabel('Confirm password', { exact: true }).fill(replacement);
  await recovery.screenshot({ path: info.outputPath('reset-mobile.png'), fullPage: true });
  await recovery.getByRole('button', { name: 'Update password', exact: true }).click();
  await expect(recovery.getByRole('status')).toContainText('Previous sessions have ended');
  expect((await page.request.get('/api/me', { headers: { Authorization: `Bearer ${old}` } })).status()).toBe(401);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await signIn(recovery, 'browser_dana', replacement);
  expect(errors).toEqual([]);
  await recovery.close();
});

for (const width of [375, 768, 1440]) {
  test(`authentication forms fit ${width}px and invalid links can be recovered`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await page.goto('/');
    await page.getByRole('button', { name: 'Create an account', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Create account' })).toBeFocused();
    await page.evaluate(async () => { await document.fonts.ready; await Promise.all(document.getAnimations().filter(a => a.effect?.getComputedTiming().iterations !== Infinity).map(a => a.finished)); });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`register-${width}.png`), fullPage: true });
    await page.goto('/#reset-password?token=invalid');
    await expect(page.getByRole('alert')).toContainText('invalid or expired');
    await page.getByRole('button', { name: 'Request a new reset link', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Forgot password?' })).toBeVisible();
    await page.screenshot({ path: info.outputPath(`forgot-${width}.png`), fullPage: true });
  });
}
