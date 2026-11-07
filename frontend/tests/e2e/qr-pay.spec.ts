import { test, expect } from '@playwright/test';
import { demoLogin } from './auth-helpers';

test('QR Pay starts with scanning and keeps the three requested actions in order', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await demoLogin(page, 'alice');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Quét mã để chuyển tiền', exact: true })).toBeVisible();
  await expect(page.locator('.qr-pay-actions button')).toHaveText(['Mã QR của tôi', 'Chuyển tiền bằng hình ảnh', 'Tải ảnh lên']);
  await expect(page.getByRole('button', { name: 'Bật camera', exact: true })).toBeVisible();
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await page.screenshot({ path: `../.local/qr-pay/scan-${width}.png` });
  }
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole('button', { name: 'Chuyển tiền bằng hình ảnh', exact: true }).click();
  await page.getByRole('button', { name: 'Chọn ảnh thông tin tài khoản', exact: false }).waitFor();
  await page.waitForTimeout(350);
  await page.screenshot({ path: '../.local/qr-pay/image-panel.png' });
  await page.keyboard.press('Escape');
  const automaticQr = page.waitForRequest(request => request.method() === 'POST' && new URL(request.url()).pathname === '/api/vietqr');
  await page.getByRole('button', { name: 'Mã QR của tôi', exact: true }).click();
  const receive = page.getByRole('dialog', { name: 'Mã QR của tôi', exact: true });
  await expect(receive).toBeVisible();
  await expect(receive.getByRole('img', { name: 'Mã QR nhận tiền NovaBank', exact: true })).toBeVisible();
  await expect(receive.getByRole('button', { name: 'Tạo mã QR', exact: true })).toHaveCount(0);
  await expect(receive.getByLabel('Số tiền', { exact: false })).toHaveCount(0);
  await expect(receive.locator('input')).toHaveCount(0);
  expect((await automaticQr).postDataJSON()).toEqual({ bank: 'NovaBank', account_no: 'ACC-ALICE-001', account_name: 'ALICE NGUYEN' });
  await page.screenshot({ path: '../.local/qr-pay/receive-panel.png' });
  await page.keyboard.press('Escape');
  await expect(receive).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Mã QR của tôi', exact: true })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('denied camera is explained without blocking upload or receive', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'BarcodeDetector', { configurable: true, value: class {
      static async getSupportedFormats() { return ['qr_code']; }
      async detect() { return []; }
    } });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { configurable: true, value: async () => { throw new DOMException('Denied', 'NotAllowedError'); } });
  });
  await demoLogin(page, 'bob');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByRole('button', { name: 'Bật camera', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('quyền camera');
  await expect(page.getByRole('button', { name: 'Tải ảnh lên', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Mã QR của tôi', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Mã QR của tôi', exact: true })).toBeVisible();
});

test('uploaded QR is validated and opens only a review, never an automatic payment', async ({ page }) => {
  await demoLogin(page, 'alice');
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const qr = await (await page.request.post('/api/vietqr', { headers: { Authorization: 'Bearer ' + token }, data: { bank: 'NovaBank', account_no: 'ACC-BOB-001', account_name: 'BOB TRAN', amount_vnd: 50000 } })).json();
  // Re-encode as JPEG: only pixels remain, so this cannot pass via PNG metadata.
  const jpeg = await page.evaluate(async image => {
    const img = new Image(); img.src = image; await img.decode();
    const canvas = document.createElement('canvas'); canvas.width = img.width; canvas.height = img.height;
    canvas.getContext('2d')!.drawImage(img, 0, 0);
    return canvas.toDataURL('image/jpeg', .95).split(',')[1];
  }, qr.image);
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByLabel('Upload NovaBank QR image', { exact: true }).setInputFiles({ name: 'bob.jpg', mimeType: 'image/jpeg', buffer: Buffer.from(jpeg, 'base64') });
  const result = page.getByRole('dialog', { name: 'Thông tin mã QR', exact: true });
  await expect(result).toContainText('ACC-BOB-001');
  await result.getByRole('button', { name: 'Kiểm tra chuyển tiền', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Transfer money', exact: true })).toBeVisible();
  await expect(page.getByLabel('NovaBank account ID')).toHaveValue('ACC-BOB-001');
  await expect(page.getByText('Transfer successful', { exact: true })).toHaveCount(0);
  await page.locator('.bank-trigger').click();
  const bankPicker = page.getByRole('dialog', { name: 'Choose a bank', exact: true });
  await bankPicker.getByRole('button').filter({ hasText: 'Demo Bank A' }).click();
  await expect(bankPicker).not.toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Transfer money', exact: true })).toBeVisible();
  await expect(page.locator('.bank-trigger')).toContainText('Demo Bank A');
  await expect(page.getByLabel('Account number', { exact: true })).toBeVisible();
});

test('local OCR reads Vietnamese account details and requires review before continuing', async ({ page }) => {
  await demoLogin(page, 'alice');
  const external: string[] = [], transfers: string[] = [], violations: string[] = [];
  const origin = new URL(page.url()).origin;
  page.context().on('request', request => {
    if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== origin) external.push(request.url());
    if (request.method() === 'POST' && /\/api\/transfers/.test(request.url())) transfers.push(request.url());
  });
  page.on('console', message => { if (/Content Security Policy|Refused to/.test(message.text())) violations.push(message.text()); });
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByRole('button', { name: 'Chuyển tiền bằng hình ảnh', exact: true }).click();
  const png = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 1100; canvas.height = 430;
    const ctx = canvas.getContext('2d')!; ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 1100, 430); ctx.fillStyle = '#222'; ctx.font = '42px Arial';
    ['Ngân hàng: Demo Bank A', 'Số tài khoản: 001234567890', 'Số tiền: 500000 VND', 'SĐT: 0912345678'].forEach((line, i) => ctx.fillText(line, 50, 85 + i * 90));
    return canvas.toDataURL().split(',')[1];
  });
  await page.getByLabel('Ảnh thông tin tài khoản', { exact: true }).setInputFiles({ name: 'account.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') });
  await expect(page.getByLabel('Số tài khoản', { exact: true })).toHaveValue('001234567890', { timeout: 45000 });
  await expect(page.getByLabel('Ngân hàng', { exact: true })).toHaveValue('DEMOA');
  await expect(page.getByRole('button', { name: 'Kiểm tra chuyển tiền', exact: true })).toBeDisabled();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole('checkbox').check();
  await page.screenshot({ path: '../.local/qr-pay/ocr-result-mobile.png' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Kiểm tra chuyển tiền', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Transfer money', exact: true })).toBeVisible();
  await expect(page.getByLabel('Account number', { exact: true })).toHaveValue('001234567890');
  expect(external).toEqual([]); expect(transfers).toEqual([]); expect(violations).toEqual([]);
});

test('camera decodes actual QR pixels without native BarcodeDetector and releases its stream', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'BarcodeDetector', { configurable: true, value: undefined }));
  await demoLogin(page, 'bob');
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const qr = await (await page.request.post('/api/vietqr', { headers: { Authorization: 'Bearer ' + token }, data: { bank: 'NovaBank', account_no: 'ACC-ALICE-001', account_name: 'ALICE NGUYEN', amount_vnd: 50000 } })).json();
  await page.evaluate(image => {
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { configurable: true, value: async () => {
      const img = new Image(); img.src = image; await img.decode();
      const canvas = document.createElement('canvas'); canvas.width = img.width; canvas.height = img.height;
      const context = canvas.getContext('2d')!;
      const stream = canvas.captureStream(15);
      const task = setInterval(() => context.drawImage(img, 0, 0), 50);
      const track = stream.getVideoTracks()[0], stop = track.stop.bind(track);
      track.stop = () => { clearInterval(task); stop(); };
      (window as unknown as { qrTestTrack: MediaStreamTrack }).qrTestTrack = track;
      return stream;
    } });
  }, qr.image);
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByRole('button', { name: 'Bật camera', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Thông tin mã QR', exact: true })).toContainText('ACC-ALICE-001');
  await expect.poll(() => page.evaluate(() => (window as unknown as { qrTestTrack: MediaStreamTrack }).qrTestTrack.readyState)).toBe('ended');
});

test('camera tracks stop when opening another QR tool', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'BarcodeDetector', { configurable: true, value: class {
      static async getSupportedFormats() { return ['qr_code']; }
      async detect() { return []; }
    } });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { configurable: true, value: async () => {
      const canvas = document.createElement('canvas'); canvas.width = 640; canvas.height = 480;
      const context = canvas.getContext('2d')!;
      const stream = canvas.captureStream(15);
      const task = setInterval(() => context.fillRect(0, 0, 640, 480), 50);
      const track = stream.getVideoTracks()[0], stop = track.stop.bind(track);
      track.stop = () => { clearInterval(task); stop(); };
      (window as unknown as { qrTestTrack: MediaStreamTrack }).qrTestTrack = track;
      return stream;
    } });
  });
  await demoLogin(page, 'bob');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByRole('button', { name: 'Bật camera', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Tắt camera', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Mã QR của tôi', exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { qrTestTrack: MediaStreamTrack }).qrTestTrack.readyState)).toBe('ended');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Bật camera', exact: true })).toBeVisible();
});

test('OCR failure and cancellation release workers and keep manual edits intact', async ({ page }) => {
  await demoLogin(page, 'bob');
  await page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name: 'QR', exact: true }).click();
  await page.getByRole('button', { name: 'Chuyển tiền bằng hình ảnh', exact: true }).click();
  const png = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 900; canvas.height = 220;
    const ctx = canvas.getContext('2d')!; ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 900, 220); ctx.fillStyle = '#222'; ctx.font = '40px Arial';
    ctx.fillText('Demo Bank A', 40, 70); ctx.fillText('Account number: 001234567890', 40, 150);
    return canvas.toDataURL().split(',')[1];
  });
  await page.context().route('**/ocr/lang/*', route => route.abort());
  await page.getByLabel('Ảnh thông tin tài khoản', { exact: true }).setInputFiles({ name: 'account.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') });
  await expect(page.getByRole('alert')).toContainText('bộ đọc ảnh', { timeout: 20000 });
  await expect.poll(() => page.workers().length).toBe(0);
  await expect(page.getByLabel('Số tài khoản', { exact: true })).toBeEnabled();
  await page.context().unroute('**/ocr/lang/*');
  const started = page.waitForEvent('worker');
  await page.getByRole('button', { name: 'Đọc lại ảnh', exact: true }).click();
  await started;
  await page.getByRole('button', { name: 'Dừng và nhập thủ công', exact: true }).click();
  await expect.poll(() => page.workers().length).toBe(0);
  await page.getByLabel('Ngân hàng', { exact: true }).selectOption('DEMOA');
  await page.getByLabel('Số tài khoản', { exact: true }).fill('987654321');
  await expect(page.getByRole('status').filter({ hasText: 'Đã dừng đọc ảnh' })).toBeVisible();
  await expect(page.getByLabel('Số tài khoản', { exact: true })).toHaveValue('987654321');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Chuyển tiền bằng hình ảnh', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Chọn ảnh thông tin tài khoản', exact: false })).toBeVisible();
  await expect(page.getByLabel('Số tài khoản', { exact: true })).toHaveCount(0);
});
