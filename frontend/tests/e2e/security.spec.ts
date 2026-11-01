import { test, expect } from '@playwright/test';
import { beginDemoLogin, completeEmailMfa, demoLogin, localMessage } from './auth-helpers';
import { createHmac } from 'node:crypto';

test.use({ actionTimeout: 10_000 });
test('MFA is required and Security Center revokes another browser session', async ({ page, browser }, info) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await beginDemoLogin(page, 'operations');
  expect(await page.evaluate(() => sessionStorage.getItem('novabank-session'))).toBeNull();
  const correct = localMessage('operations@novabank.test', 'LOGIN_OTP').code;
  await page.getByLabel('Verification code', { exact: true }).fill(correct === '111111' ? '222222' : '111111');
  await page.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('invalid');
  await page.screenshot({ path: info.outputPath('mfa-mobile.png'), fullPage: true, animations: 'disabled' });
  expect(await page.evaluate(() => sessionStorage.getItem('novabank-session'))).toBeNull();
  await completeEmailMfa(page, 'operations@novabank.test');
  await page.setViewportSize({ width: 1440, height: 900 });
  const other = await browser.newPage({ baseURL: 'http://127.0.0.1:8092', viewport: { width: 375, height: 812 } });
  await demoLogin(other, 'operations');
  await other.getByRole('button', { name: 'Profile', exact: true }).click();
  await expect(other.getByRole('heading', { name: 'Security Center', exact: true })).toBeVisible();
  await expect(other.getByRole('region', { name: 'Active sessions', exact: true }).locator('.session-row')).toHaveCount(2);
  await other.getByRole('heading', { name: 'Active sessions', exact: true }).scrollIntoViewIfNeeded();
  expect(await other.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await other.screenshot({ path: info.outputPath('security-mobile.png'), fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  const section = page.getByRole('region', { name: 'Active sessions', exact: true });
  await expect(section.locator('.session-row')).toHaveCount(2);
  await section.getByRole('button', { name: 'Sign out session', exact: true }).click();
  await section.getByRole('button', { name: 'Confirm sign out', exact: true }).click();
  await expect(section.locator('.session-row')).toHaveCount(1);
  await page.screenshot({ path: info.outputPath('security-desktop.png'), fullPage: true, animations: 'disabled' });
  await other.reload();
  await expect(other.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Login history', exact: true })).toContainText('Successful sign-in');
  await other.close();
});

// Independent test authenticator. Backend primitives are already covered by RFC 6238 vectors.
function authenticatorCode(secret: string, stepOffset = 0) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret].map(character => alphabet.indexOf(character).toString(2).padStart(5, '0')).join('');
  const bytes = Buffer.from(bits.match(/.{8}/g)!.map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + stepOffset));
  const mac = createHmac('sha1', bytes).update(counter).digest();
  const offset = mac[mac.length - 1] & 15;
  return String((mac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, '0');
}

test('authenticator setup, sign-in, email fallback and disabling use real MFA', async ({ page, browser }, info) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await demoLogin(page, 'support');
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await page.getByRole('button', { name: 'Set up authenticator', exact: true }).click();
  await page.getByLabel('Current password', { exact: true }).fill('Support@2026');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  const secret = await page.getByLabel('Setup key', { exact: true }).inputValue();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: info.outputPath('authenticator-setup-mobile.png'), fullPage: true, animations: 'disabled', mask: [page.getByLabel('Setup key', { exact: true })] });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByLabel('Authenticator code', { exact: true }).fill(authenticatorCode(secret, -1));
  await page.getByRole('button', { name: 'Enable authenticator', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Sign-in verification', exact: true })).toContainText('Authenticator enabled');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole('heading', { name: 'Sign-in verification', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('authenticator-enabled.png'), fullPage: true, animations: 'disabled' });
  const alternate = await browser.newPage({ baseURL: 'http://127.0.0.1:8092' });
  await alternate.goto('/');
  await alternate.getByLabel('Username', { exact: true }).fill('support');
  await alternate.getByLabel('Password', { exact: true }).fill('Support@2026');
  await alternate.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(alternate.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
  await alternate.getByLabel('Verification code', { exact: true }).fill(authenticatorCode(secret));
  await alternate.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(alternate.getByRole('navigation', { name: 'Main', exact: true })).toBeVisible();
  await alternate.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(alternate.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await alternate.getByLabel('Username', { exact: true }).fill('support');
  await alternate.getByLabel('Password', { exact: true }).fill('Support@2026');
  await alternate.getByRole('button', { name: 'Sign in', exact: true }).click();
  await alternate.getByRole('button', { name: 'Use an email code instead', exact: true }).click();
  await expect(alternate.getByRole('status')).toContainText('new code');
  await completeEmailMfa(alternate, 'support@novabank.test');

  await page.getByRole('button', { name: 'Disable authenticator', exact: true }).click();
  await page.getByLabel('Current password', { exact: true }).fill('Support@2026');
  // Exercise a pending real request; inbox reads must not rely on Python startup latency.
  await page.route('**/api/auth/mfa/disable-request', async route => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    await route.continue();
  });
  await page.getByRole('button', { name: 'Send confirmation code', exact: true }).click();
  await expect(page.getByLabel('Email confirmation code', { exact: true })).toBeVisible();
  await page.getByLabel('Email confirmation code', { exact: true }).fill(localMessage('support@novabank.test', 'DISABLE_TOTP_OTP').code);
  await page.getByRole('button', { name: 'Confirm disable', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Sign-in verification', exact: true })).toContainText('Email codes enabled');
  await alternate.reload();
  await expect(alternate.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
  await alternate.close();
});

test('browser rotates expired access credentials, revokes logout and expires idle sessions', async ({ page }) => {
  await demoLogin(page, 'auditor');
  const before = await page.evaluate(() => {
    const saved = JSON.parse(sessionStorage.getItem('novabank-session')!);
    sessionStorage.setItem('novabank-session', JSON.stringify({ ...saved, expiresAt: 0 }));
    return saved;
  });
  await page.reload();
  await expect.poll(() => page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!)?.refreshToken)).not.toBe(before.refreshToken);
  await expect(page.getByRole('heading', { name: 'Operations', exact: true })).toBeVisible();
  const after = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!));
  expect(after.id).toBe('auditor');
  expect(after.sessionId).toBe(before.sessionId);
  expect(after.idleExpiresAt).toBe(before.idleExpiresAt);
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  expect((await page.request.get('/api/me', { headers: { Authorization: `Bearer ${after.token}` } })).status()).toBe(401);
  expect((await page.request.post('/api/auth/refresh', { data: { refresh_token: after.refreshToken } })).status()).toBe(401);
  await demoLogin(page, 'auditor');
  await page.clock.install();
  await page.clock.fastForward(300_001);
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('novabank-session'))).toBeNull();
});
