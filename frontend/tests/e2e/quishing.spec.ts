import { createHmac } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from './quishing-fixture';
import { demoLogin, enterTransactionPin } from './auth-helpers';
import { pythonExecutable } from './python';

test.use({ video: 'on' });

test('malicious signed QR image is blocked without opening its URL or drafting payment', async ({ page, qrBank }, info) => {
  await demoLogin(page, 'alice');
  const raw = Buffer.from(JSON.stringify({ bank: 'NovaBank', account_no: 'ACC-BOB-001', amount_vnd: 10000,
    account_name: 'BOB TRAN', add_info: 'https://evil.example/pay' })).toString('base64url');
  const payload = 'NBQR1:' + raw + '.' + createHmac('sha256', qrBank.signingKey).update('NBQR1:' + raw).digest('hex');
  const root = resolve('..');
  const python = pythonExecutable(root);
  const image = execFileSync(python, ['-c', 'import sys; from app.local_qr import png; sys.stdout.buffer.write(png(sys.argv[1]))', payload], { cwd: resolve(root, 'backend') });
  const destinations: string[] = [], payments: string[] = [];
  page.on('request', request => {
    if (request.url().includes('evil.example')) destinations.push(request.url());
    if (request.method() === 'POST' && /\/api\/transfers(?:\/|$)/.test(request.url())) payments.push(request.url());
  });
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByLabel('Upload NovaBank QR image', { exact: true }).setInputFiles({ name: 'hostile.png', mimeType: 'image/png', buffer: image });
  await expect(page.getByRole('alert')).toContainText('UNSAFE_QR_CONTENT');
  await page.screenshot({ path: info.outputPath('malicious-qr-blocked.png'), fullPage: true, animations: 'disabled' });
  await expect(page.getByRole('dialog', { name: 'Thông tin mã QR', exact: true })).toHaveCount(0);
  expect(destinations).toEqual([]);
  expect(payments).toEqual([]);
});

test('genuine external QR shows source/new-recipient caution and reaches separate verification', async ({ page }, info) => {
  await demoLogin(page, 'alice');
  const access = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const headers = { Authorization: 'Bearer ' + access };
  const qr = await (await page.request.post('/api/vietqr', { headers, data: { bank: 'Demo Bank A', account_no: '00123456789', account_name: 'LOTUS BOOK SHOP', amount_vnd: 50000, add_info: 'Books' } })).json();
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByLabel('Upload NovaBank QR image', { exact: true }).setInputFiles({ name: 'genuine.png', mimeType: 'image/png', buffer: Buffer.from(qr.image.split(',')[1], 'base64') });
  const review = page.getByRole('dialog', { name: 'Thông tin mã QR', exact: true });
  await expect(review).toContainText('Dữ liệu này đến từ QR');
  await expect(review.getByRole('alert')).toContainText('Người nhận ngân hàng ngoài');
  await page.screenshot({ path: info.outputPath('genuine-qr-review.png'), fullPage: true, animations: 'disabled' });
  await review.getByRole('button', { name: 'Kiểm tra chuyển tiền', exact: true }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Continue to verification', exact: true }).click();
  await enterTransactionPin(page, 'alice');
  await expect(page.getByRole('button', { name: 'Confirm transfer', exact: true })).toBeEnabled();
  await page.screenshot({ path: info.outputPath('genuine-qr-verification.png'), fullPage: true, animations: 'disabled' });
  await expect(page.getByText('Transfer successful', { exact: true })).toHaveCount(0);
  const me = await (await page.request.get('/api/me', { headers })).json();
  expect(me.accounts[0].balance_vnd).toBe(10000000);
});
