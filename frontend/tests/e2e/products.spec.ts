import { test, expect, type Page } from './fixtures';
import { demoLogin, enterTransactionPin, localMessage } from './auth-helpers';

async function explore(page: Page, name: string) {
  const nav = page.getByRole('navigation', { name: 'Main', exact: true });
  const item = nav.getByRole('button', { name: 'Explore', exact: true });
  // Phones have no Explore tab; Home's "All services" tile opens the same page.
  if (await item.isVisible()) await item.click();
  else {
    await nav.getByRole('button', { name: 'Home', exact: true }).click();
    await page.getByRole('button', { name: 'All services', exact: true }).click();
  }
  await page.getByRole('button', { name, exact: false }).click();
}
// A real drop event carrying one file onto the Nova bubble. The page CSP blocks fetch() of data: URLs.
async function dropOnNova(page: Page, dataUrl: string, name: string, type: string) {
  await page.getByRole('button', { name: 'Open Nova assistant', exact: true }).evaluate((target, file) => {
    const bytes = Uint8Array.from(atob(file.dataUrl.split(',')[1]), c => c.charCodeAt(0));
    const transfer = new DataTransfer();
    transfer.items.add(new File([bytes], file.name, { type: file.type }));
    target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: transfer }));
  }, { dataUrl, name, type });
}
async function confirmAction(page: Page, kind: string) {
  const dialog = page.getByRole('dialog', { name: 'Review and confirm', exact: true });
  await expect(dialog).toBeVisible();
  void kind;
  await enterTransactionPin(dialog, 'bob');
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
  await page.getByRole('button', { name: 'Continue to verification', exact: true }).click();
  await confirmAction(page, 'PAY_BILL');
  await expect(bill.getByText('paid', { exact: true })).toBeVisible();
  await expect(bill.getByRole('button', { name: 'Review payment' })).toHaveCount(0);
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Savings Build', exact: false }).click();
  await page.getByRole('button', { name: 'Open savings', exact: true }).click();
  await page.getByLabel('Savings name').fill('Browser test fund');
  await page.getByLabel('Deposit (VND)').fill('1000000');
  await page.getByRole('button', { name: 'Review savings deposit' }).click();
  await confirmAction(page, 'OPEN_SAVINGS');
  const savings = page.locator('article').filter({ has: page.getByRole('heading', { name: 'Browser test fund' }) });
  await expect(savings.locator('.service-amount')).toHaveText('1,000,000 VND');
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
  // Nova bubble shares this sign-in: the suite stays under the 20 MFA verifications per 15 min limit.
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const qr = await (await page.request.post('/api/vietqr', { headers: { Authorization: 'Bearer ' + token },
    data: { bank: 'NovaBank', account_no: 'ACC-BOB-001', account_name: 'BOB TRAN', amount_vnd: 50000 } })).json();
  await dropOnNova(page, 'data:text/plain;base64,aGVsbG8=', 'note.txt', 'text/plain');
  await expect(page.getByRole('alert')).toContainText('NovaBank QR image');
  await page.getByRole('dialog', { name: 'Nova assistant' }).getByRole('button', { name: 'Close', exact: true }).click();
  await dropOnNova(page, qr.image, 'qr.png', 'image/png');
  await expect(page.getByLabel('NovaBank account ID')).toHaveValue('ACC-BOB-001');
  await page.keyboard.press('Escape');
  await explore(page, 'Accounts & recipients');
  await page.getByRole('button', { name: 'Add a recipient', exact: true }).click();
  await page.getByLabel('Account ID or number').fill('ACC-ALICE-001');
  await page.getByLabel('Nickname', { exact: true }).fill('Alice test');
  await page.getByRole('button', { name: 'Verify and save recipient' }).click();
  await expect(page.getByText('ALICE NGUYEN', { exact: false })).toBeVisible();
  const recipient = page.locator('li').filter({ hasText: 'Alice test' });
  await recipient.getByRole('button', { name: 'Edit nickname' }).click();
  await page.getByLabel('Recipient nickname').fill('Alice saved');
  await page.getByRole('button', { name: 'Save nickname', exact: true }).click();
  await expect(page.getByText('Alice saved', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Rename account', exact: true }).click();
  await page.getByLabel('Account nickname').fill('Everyday account');
  await page.getByRole('button', { name: 'Save nickname', exact: true }).click();
  await page.reload(); await explore(page, 'Accounts & recipients');
  await expect(page.getByRole('heading', { name: 'Everyday account', exact: true })).toBeVisible();
  const savedRecipient = page.locator('li').filter({ hasText: 'Alice saved' });
  await savedRecipient.getByRole('button', { name: 'Transfer', exact: true }).click();
  await expect(page.getByLabel('NovaBank account ID', { exact: true })).toHaveValue('ACC-ALICE-001');
  await page.keyboard.press('Escape');
  await explore(page, 'Accounts & recipients');
  await savedRecipient.getByRole('button', { name: 'Remove', exact: true }).click();
  await page.getByRole('dialog', { name: 'Remove recipient?', exact: true }).getByRole('button', { name: 'Remove', exact: true }).click();
  await expect(savedRecipient).toHaveCount(0);
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Demo QR Receive', exact: false }).click();
  await page.getByRole('button', { name: 'Mã QR của tôi', exact: true }).click();
  await expect(page.getByRole('img', { name: 'Mã QR nhận tiền NovaBank', exact: true })).toBeVisible();
  await page.getByText('Nội dung mã QR', { exact: true }).click();
  const payload = page.getByLabel('QR text for sharing', { exact: true });
  await expect(payload).toHaveValue(/^NBQR1:/);
  const qrText = await payload.inputValue();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Dán nội dung mã QR', exact: true }).click();
  await page.getByLabel('QR text', { exact: true }).fill(qrText);
  await page.getByRole('button', { name: 'Đọc mã QR', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Kiểm tra chuyển tiền', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'All services', exact: true }).click();
  await page.getByRole('button', { name: 'Help & support', exact: false }).click();
  await page.getByRole('button', { name: 'New support request', exact: true }).click();
  await page.getByLabel('Subject', { exact: true }).fill('Browser support acceptance');
  await page.getByLabel('What happened?').fill('Please review my simulated payment.');
  await page.getByRole('button', { name: 'Create ticket', exact: true }).click();
  const ticket = page.getByRole('dialog', { name: 'Support ticket', exact: true });
  await expect(ticket.getByRole('heading', { name: 'Browser support acceptance' })).toBeVisible();
  await ticket.getByLabel('Add PNG, JPEG, PDF or text (up to 2 MB)').setInputFiles({ name: 'payment-note.txt', mimeType: 'text/plain', buffer: Buffer.from('Please review this simulated payment.') });
  await expect(ticket.getByText('payment-note.txt', { exact: false })).toBeVisible();
  await page.screenshot({ path: '../.local/explore/support-ticket-mobile.png', animations: 'disabled' });
  const attachment = page.waitForEvent('download');
  await ticket.getByRole('button', { name: 'Download', exact: true }).click();
  expect((await attachment).suggestedFilename()).toBe('payment-note.txt');
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
