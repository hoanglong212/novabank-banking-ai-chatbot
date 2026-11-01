import { test, expect, type Page } from '@playwright/test';
import { demoLogin, localMessage } from './auth-helpers';

async function explore(page: Page, name: string) {
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Explore', exact: true }).click();
  await page.getByRole('button', { name, exact: false }).click();
}
async function confirmAction(page: Page, kind: string) {
  const dialog = page.getByRole('dialog', { name: 'Review and confirm', exact: true });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('Verification code', { exact: true }).fill(localMessage('bob@novabank.test', 'ACTION_' + kind).code);
  await dialog.getByRole('button', { name: 'Confirm action', exact: true }).click();
  await expect(dialog).not.toBeVisible();
}

test('products: bills, savings, card confirmation and statements', async ({ page }) => {
  await demoLogin(page, 'bob');
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await page.getByLabel('Saved bill reminders', { exact: true }).uncheck();
  await page.getByRole('button', { name: 'Save notification preferences', exact: true }).click();
  await expect(page.getByText('Notification preferences saved.', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await expect(page.getByLabel('Saved bill reminders', { exact: true })).not.toBeChecked();
  await explore(page, 'Pay bills');
  const bill = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Nova Energy', exact: true }) });
  await bill.getByRole('button', { name: 'Review payment', exact: true }).click();
  await confirmAction(page, 'PAY_BILL');
  await expect(bill.getByText('paid', { exact: true })).toBeVisible();
  await expect(bill.getByRole('button', { name: 'Review payment' })).toHaveCount(0);
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Savings Build', exact: false }).click();
  await page.getByLabel('Savings name').fill('Browser test fund');
  await page.getByLabel('Deposit (VND)').fill('1000000');
  await page.getByRole('button', { name: 'Review savings deposit' }).click();
  await confirmAction(page, 'OPEN_SAVINGS');
  const savings = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Browser test fund' }) });
  await expect(savings.getByText('1,000,000 VND', { exact: true })).toBeVisible();
  await savings.getByRole('button', { name: 'Review withdrawal' }).click();
  await confirmAction(page, 'WITHDRAW_SAVINGS');
  await expect(savings.getByText('closed', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Cards Manage', exact: false }).click();
  const card = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Nova debit' }) });
  await card.getByRole('button', { name: 'Freeze card', exact: true }).click();
  await confirmAction(page, 'FREEZE_CARD');
  await expect(card.getByText('frozen', { exact: true })).toBeVisible();
  await card.getByRole('button', { name: 'Unfreeze card', exact: true }).click();
  await confirmAction(page, 'UNFREEZE_CARD');
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Statements Download', exact: false }).click();
  await page.getByLabel('From', { exact: true }).fill('2026-01-01');
  await page.getByLabel('To', { exact: true }).fill('2026-12-31');
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download statement', exact: true }).click();
  expect((await downloaded).suggestedFilename()).toBe('NovaBank-statement.pdf');
});

test('mobile services: saved recipient, internal QR, support and admin response', async ({ page, browser }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await demoLogin(page, 'bob');
  await explore(page, 'Accounts & recipients');
  await page.getByLabel('Account ID or number').fill('ACC-ALICE-001');
  await page.getByLabel('Nickname', { exact: true }).fill('Alice test');
  await page.getByRole('button', { name: 'Verify and save recipient' }).click();
  await expect(page.getByText('ALICE NGUYEN', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Demo QR Receive', exact: false }).click();
  await page.getByRole('button', { name: 'Create demo QR' }).click();
  const payload = page.getByLabel('QR text for sharing', { exact: true });
  await expect(payload).toHaveValue(/^NBQR1:/);
  await page.getByLabel('QR text', { exact: true }).fill(await payload.inputValue());
  await page.getByRole('button', { name: 'Read code', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Review transfer', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Help & support', exact: false }).click();
  await page.getByLabel('Subject', { exact: true }).fill('Browser support acceptance');
  await page.getByLabel('What happened?').fill('Please review my simulated payment.');
  await page.getByRole('button', { name: 'Create ticket', exact: true }).click();
  const ticket = page.getByRole('dialog', { name: 'Support ticket', exact: true });
  await expect(ticket.getByRole('heading', { name: 'Browser support acceptance' })).toBeVisible();
  await ticket.getByRole('button', { name: 'Close', exact: true }).click();
  const context = await browser.newContext(); const staff = await context.newPage();
  await demoLogin(staff, 'support');
  const row = staff.locator('li').filter({ has: staff.getByText('Browser support acceptance', { exact: true }) });
  await row.getByRole('button', { name: 'Open ticket' }).click();
  await staff.getByLabel('Reply', { exact: true }).fill('Your demo payment was reviewed.');
  await staff.getByRole('button', { name: 'Send reply' }).click();
  await expect(staff.getByText('Your demo payment was reviewed.', { exact: true })).toBeVisible();
  await context.close();
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await page.locator('li').filter({ has: page.getByText('Browser support acceptance', { exact: true }) }).getByRole('button', { name: 'Open ticket' }).click();
  await expect(ticket.getByText('Your demo payment was reviewed.', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
