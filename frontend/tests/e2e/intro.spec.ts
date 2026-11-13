import { test, expect } from './fixtures';

test('opens with the introduction, then loading, then the interactive login', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('region', { name: 'NovaBank introduction' })).toBeVisible();
  await expect(page.getByLabel('Username', { exact: true })).toHaveCount(0);
  await expect(page.locator('.nova-intro-player svg')).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Opening NovaBank…');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Alice', exact: true }).click();
  await expect(page.getByLabel('Username', { exact: true })).toHaveValue('alice');
});

test('a missing intro asset never blocks sign in', async ({ page }) => {
  await page.route('**/animations/nova-intro-vector/animation.json', route => route.abort());
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible({ timeout: 1500 });
});

test('vector intro stays sharp at high DPR and never loads raster frames', async ({ browser }) => {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  const rasterRequests: string[] = [];
  page.on('request', request => { if (/\.(webp|png|jpe?g)(\?|$)/.test(request.url())) rasterRequests.push(request.url()); });
  await page.goto('/');
  const svg = page.locator('.nova-intro-player > svg');
  await expect(svg).toBeVisible();
  await expect(svg).toHaveAttribute('viewBox', '0 0 1280 720');
  await expect(svg.locator('image')).toHaveCount(0);
  expect(await svg.locator('path').count()).toBeGreaterThan(10);
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(svg).toHaveAttribute('preserveAspectRatio', 'xMidYMid meet');
  await expect.poll(() => svg.evaluate(element => {
    const rect = element.getBoundingClientRect();
    return Math.abs(rect.x + rect.width / 2 - innerWidth / 2);
  })).toBeLessThan(1);
  expect(rasterRequests).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.setViewportSize({ width: 1920, height: 1080 });
  await expect(page.getByRole('heading', { name: 'Sign in to pick up the conversation.' })).toBeVisible();
  await expect(page.locator('.auth-editorial img')).toHaveCount(0);
  await page.close();
});

test('skip opens login immediately, reload stays there, replay is explicit', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Skip introduction', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('region', { name: 'NovaBank introduction' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Replay introduction', exact: true }).click();
  await expect(page.getByRole('region', { name: 'NovaBank introduction' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});

test('reduced motion and recovery links bypass the intro', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'NovaBank introduction' })).toHaveCount(0);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.evaluate(() => sessionStorage.clear());
  await page.goto('/#reset-password?token=' + 'a'.repeat(43));
  await expect(page.getByRole('heading', { name: 'Choose a new password', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'NovaBank introduction' })).toHaveCount(0);
});
