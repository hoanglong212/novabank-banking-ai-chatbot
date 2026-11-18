import { test, expect } from './fixtures';
import { demoLogin } from './auth-helpers';

test('Documents upload, status, question selection and deletion on desktop and mobile', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await demoLogin(page, 'alice');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Assistant', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Attach document', exact: true })).toBeVisible({ timeout: 2500 });
  await page.getByRole('button', { name: 'Attach document', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'My documents', exact: true })).toBeVisible();
  await page.getByLabel('Choose a document').setInputFiles({
    name: 'invoice.txt', mimeType: 'text/plain', buffer: Buffer.from('Invoice total 150,000 VND. Date 2026-11-18.'),
  });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  const row = page.getByRole('article').filter({ hasText: 'invoice.txt' });
  await expect(row.getByText('Ready', { exact: true })).toBeVisible();
  for (const width of [1440, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole('button', { name: 'Ask about document', exact: true })).toBeVisible();
    expect(await page.locator('body').evaluate(el => el.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: '../.local/documents-' + width + '.png', fullPage: true, animations: 'disabled' });
  }
  await page.getByLabel('Question about invoice.txt').fill('What is the invoice total?');
  await row.getByRole('button', { name: 'Ask about document', exact: true }).click();
  await expect(page).toHaveURL(/\/assistant$/);
  await page.getByRole('button', { name: 'Attach document', exact: true }).click();
  await row.getByRole('button', { name: 'Delete invoice.txt', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Remove', exact: true }).click();
  await expect(row).toHaveCount(0);
});
