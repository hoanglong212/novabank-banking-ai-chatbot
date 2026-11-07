import { test, expect } from '@playwright/test';

async function openVerify(page: import('@playwright/test').Page) {
  await page.addInitScript(() => sessionStorage.setItem('novabank-intro-seen', '1'));
  await page.route('**/api/auth/login', route => route.fulfill({ json: {
    mfa_required: true, challenge_id: 'motion-test', method: 'email', expires_in: 300,
    message: 'Enter your verification code.',
  } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Alice', exact: true }).click();
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Verify sign-in', exact: true })).toBeVisible();
}

test('each verify digit animates independently and native editing still works', async ({ page }) => {
  await openVerify(page);
  const input = page.getByLabel('Verification code', { exact: true });
  const slots = page.locator('.auth-otp-slot');
  await expect(slots).toHaveCount(6);
  await input.focus();
  await input.pressSequentially('12');
  await expect(input).toHaveValue('12');
  await expect(slots.nth(0)).toHaveText('1');
  await expect(slots.nth(1)).toHaveText('2');
  const firstDigit = await slots.nth(0).locator('.auth-otp-digit').elementHandle();
  await input.press('3');
  expect(await firstDigit!.evaluate(node => node.isConnected)).toBe(true);
  expect(await slots.nth(2).locator('.auth-otp-digit').evaluate(node => getComputedStyle(node).animationName)).toBe('auth-otp-digit-enter');
  await input.press('Backspace');
  await expect(input).toHaveValue('12');
  await input.pressSequentially('3456');
  await expect(page.getByRole('button', { name: 'Verify and sign in', exact: true })).toBeEnabled();
  await input.press('ArrowLeft');
  await input.press('Backspace');
  await expect(input).toHaveValue('12346');
  await input.fill('654321');
  await expect(slots.nth(5)).toHaveText('1');
  const bounds = await input.boundingBox();
  await page.mouse.click(bounds!.x + bounds!.width / 6 * 2.5, bounds!.y + bounds!.height / 2);
  await input.press('9');
  await expect(input).toHaveValue('659321');
  await input.fill('012345');
  await expect(slots.nth(0)).toHaveText('0');
});

test('pasting a formatted code, invalid response and reduced motion remain accessible', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 812 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.route('**/api/auth/mfa/verify', route => route.fulfill({ status: 400, json: { detail: 'Invalid verification code.' } }));
  await openVerify(page);
  const input = page.getByLabel('Verification code', { exact: true });
  await input.evaluate(element => {
    const data = new DataTransfer(); data.setData('text', '123 456');
    element.dispatchEvent(new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true }));
  });
  await expect(input).toHaveValue('123456');
  expect(await page.locator('.auth-otp-digit').first().evaluate(node => getComputedStyle(node).animationName)).toBe('none');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Verify and sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Invalid');
  await expect(input).toHaveValue('');
  await expect(input).toHaveAttribute('aria-invalid', 'true');
});
