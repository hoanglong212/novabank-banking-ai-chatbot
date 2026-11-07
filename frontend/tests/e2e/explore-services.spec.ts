import { test, expect, type Page } from '@playwright/test';
import { demoLogin, enterTransactionPin, localMessage } from './auth-helpers';

async function service(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Home', exact: true }).click();
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.locator('.explore-directory').getByRole('button', { name, exact: false }).click();
  await expect(page.getByText('Loading…', { exact: true })).toHaveCount(0);
}
async function confirm(page: Page, kind: string, user = 'alice') {
  const dialog = page.getByRole('dialog', { name: 'Review and confirm', exact: true });
  await expect(dialog).toBeVisible();
  void kind;
  await enterTransactionPin(dialog, user);
  await dialog.getByRole('button', { name: 'Confirm action', exact: true }).click();
  await expect(dialog).not.toBeVisible();
}

test('Explore directory and every service render at desktop and mobile widths', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const failures: string[] = []; page.on('pageerror', error => failures.push(error.message));
  await demoLogin(page, 'alice');
  const sections = ['Accounts & recipients', 'Cards', 'Pay bills', 'Savings', 'Spending & budgets', 'Goals & calculator', 'Statements', 'Demo QR', 'Help & support'];
  for (const width of [1440, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 });
    await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Home', exact: true }).click();
    await page.getByRole('button', { name: 'All services', exact: true }).click();
    await expect(page.locator('.explore-service')).toHaveCount(9);
    await page.getByLabel('Search services').fill('not-a-service');
    await expect(page.getByText('No matching service', { exact: true })).toBeVisible();
    await page.getByLabel('Search services').fill('');
    await page.screenshot({ path: `../.local/explore/directory-${width}.png`, fullPage: true, animations: 'disabled' });
    for (const [index, name] of sections.entries()) {
      await service(page, name);
      await expect(page.getByRole('button', { name: 'All services', exact: true })).toBeVisible();
      await page.screenshot({ path: `../.local/explore/service-${index}-${width}.png`, fullPage: true, animations: 'disabled' });
      await page.locator('#main').evaluate(el => { el.scrollTop = el.scrollHeight; });
      await page.screenshot({ path: `../.local/explore/service-${index}-${width}-bottom.png`, fullPage: true, animations: 'disabled' });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (name === 'Cards') expect(await page.locator('.product-card .detail-list').evaluateAll(lists => lists.every(list => list.getBoundingClientRect().right <= list.closest('article')!.getBoundingClientRect().right))).toBe(true);
    }
  }
  expect(failures).toEqual([]);
});

test('goals track a real deposit, can be edited and removed, and budgets persist', async ({ page }) => {
  await demoLogin(page, 'alice');
  await service(page, 'Savings');
  await page.getByRole('button', { name: 'Open savings', exact: true }).click();
  await page.getByLabel('Savings name').fill('Explore linked fund');
  await page.getByLabel('Deposit (VND)').fill('1000000');
  await page.getByRole('button', { name: 'Review savings deposit', exact: true }).click();
  await confirm(page, 'OPEN_SAVINGS');
  await expect(page.getByRole('heading', { name: 'Explore linked fund', exact: true })).toBeVisible();
  await service(page, 'Goals & calculator');
  await page.getByRole('button', { name: 'Create goal', exact: true }).click();
  const editor = page.getByRole('dialog', { name: 'Create a savings goal', exact: true });
  await editor.getByLabel('Goal name').fill('Explore trip');
  await editor.getByLabel('Target (VND)').fill('2000000');
  await editor.getByLabel('Target date').fill('2030-01-01');
  await editor.getByLabel('Link a savings account').selectOption({ label: 'Explore linked fund' });
  await editor.getByRole('button', { name: 'Create goal', exact: true }).click();
  let goal = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Explore trip', exact: true }) });
  await expect(goal).toContainText('50% complete');
  await goal.getByRole('button', { name: 'Edit goal', exact: true }).click();
  await page.getByLabel('Goal name').fill('Explore trip edited');
  await page.getByRole('button', { name: 'Save goal', exact: true }).click();
  await page.reload(); await service(page, 'Goals & calculator');
  goal = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Explore trip edited', exact: true }) });
  await expect(goal).toContainText('50% complete');
  await goal.getByRole('button', { name: 'Remove goal', exact: true }).click();
  await page.getByRole('dialog', { name: 'Remove savings goal?', exact: true }).getByRole('button', { name: 'Remove', exact: true }).click();
  await expect(goal).toHaveCount(0);
  await service(page, 'Savings');
  await expect(page.getByRole('heading', { name: 'Explore linked fund', exact: true })).toBeVisible();
  await service(page, 'Spending & budgets');
  await page.getByRole('button', { name: 'Set budget', exact: true }).click();
  await page.getByLabel('Category', { exact: true }).selectOption('food');
  await page.getByLabel('Monthly limit (VND)').fill('300000');
  await page.getByRole('button', { name: 'Save budget', exact: true }).click();
  await page.getByRole('button', { name: 'Edit food budget', exact: true }).click();
  await page.getByLabel('Monthly limit (VND)').fill('400000');
  await page.getByRole('button', { name: 'Save budget', exact: true }).click();
  await page.reload(); await service(page, 'Spending & budgets');
  await expect(page.locator('.budget-line').filter({ hasText: 'Food' })).toContainText('400,000 VND');
});

test('card purchase and repayment change real credit state and statements download CSV', async ({ page }) => {
  await demoLogin(page, 'bob');
  await service(page, 'Cards');
  const credit = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Nova credit', exact: true }) });
  await credit.getByRole('button', { name: 'Simulate purchase', exact: true }).click();
  await page.getByLabel('Amount (VND)', { exact: true }).fill('50000');
  await page.getByLabel('Merchant or description', { exact: true }).fill('Explore coffee');
  await page.getByRole('button', { name: 'Review action', exact: true }).click();
  await confirm(page, 'CARD_PURCHASE', 'bob');
  await credit.getByRole('button', { name: 'Repay credit balance', exact: true }).click();
  await page.getByLabel('Amount (VND)', { exact: true }).fill('50000');
  await page.getByRole('button', { name: 'Review action', exact: true }).click();
  await confirm(page, 'REPAY_CARD', 'bob');
  await credit.locator('summary').click();
  await expect(credit.getByText('Explore coffee', { exact: true })).toBeVisible();
  await expect(credit.getByText('Credit repayment', { exact: true })).toBeVisible();
  await service(page, 'Statements');
  await page.getByLabel('From', { exact: true }).fill('2030-01-02');
  await page.getByLabel('To', { exact: true }).fill('2030-01-01');
  await expect(page.getByRole('button', { name: 'Download statement', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'This month', exact: true }).click();
  await page.getByLabel('Format', { exact: true }).selectOption('csv');
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download statement', exact: true }).click();
  expect((await downloaded).suggestedFilename()).toBe('NovaBank-statement.csv');
});
