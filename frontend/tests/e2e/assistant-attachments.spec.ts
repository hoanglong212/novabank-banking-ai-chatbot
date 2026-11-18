import { test, expect } from './fixtures';
import { demoLogin } from './auth-helpers';

test('Assistant accepts document and QR drops and requires bank review before payment', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await demoLogin(page, 'alice');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'Assistant', exact: true }).click();
  const chat = page.getByRole('region', { name: 'Chat with Nova' });
  const uploads: string[] = [];
  const transferWrites: string[] = [];
  page.on('request', request => {
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST' && path === '/api/documents') uploads.push(path);
    if (request.method() === 'POST' && path.startsWith('/api/transfers')) transferWrites.push(path);
  });
  await chat.evaluate(target => {
    const files = new DataTransfer();
    files.items.add(new File(['Invoice total 150,000 VND.'], 'dropped-invoice.txt', { type: 'text/plain' }));
    target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: files }));
  });
  const documents = page.getByRole('dialog', { name: 'My documents', exact: true });
  await expect(documents.getByText('dropped-invoice.txt', { exact: true })).toBeVisible({ timeout: 3500 });
  expect(uploads).toHaveLength(0);
  await documents.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(documents.getByRole('article').filter({ hasText: 'dropped-invoice.txt' }).getByText('Ready', { exact: true })).toBeVisible();
  await documents.getByRole('button', { name: 'Close', exact: true }).click();

  await expect(page.getByRole('button', { name: 'Upload QR image', exact: true })).toBeVisible();
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const created = await page.request.post('/api/vietqr', {
    headers: { Authorization: 'Bearer ' + token },
    data: { bank: 'NovaBank', account_no: 'ACC-BOB-001', account_name: 'BOB TRAN', amount_vnd: 50000 },
  });
  expect(created.ok()).toBe(true);
  const { image } = await created.json();
  await page.getByLabel('Choose a QR image', { exact: true }).setInputFiles({
    name: 'bob.png', mimeType: 'image/png', buffer: Buffer.from(image.split(',')[1], 'base64'),
  });
  const preview = page.getByRole('dialog', { name: 'Thông tin mã QR', exact: true });
  await expect(preview).toContainText('ACC-BOB-001');
  await preview.getByRole('button', { name: 'Close', exact: true }).click();
  await chat.evaluate((target, dataUrl) => {
    const bytes = Uint8Array.from(atob(dataUrl.split(',')[1]), c => c.charCodeAt(0));
    const files = new DataTransfer();
    files.items.add(new File([bytes], 'bob.png', { type: 'image/png' }));
    target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: files }));
  }, image);
  await expect(preview).toContainText('ACC-BOB-001');
  expect(transferWrites).toHaveLength(0);
  await preview.getByRole('button', { name: 'Kiểm tra chuyển tiền', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Transfer money', exact: true })).toBeVisible();
  await expect(page.getByLabel('NovaBank account ID')).toHaveValue('ACC-BOB-001');
  expect(transferWrites).toHaveLength(0);
});
