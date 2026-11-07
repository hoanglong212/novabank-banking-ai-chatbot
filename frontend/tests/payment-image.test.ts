import assert from 'node:assert/strict';
import { paymentImageText } from '../src/components/qr/paymentImageText';
import type { Bank } from '../src/types';

export function checkPaymentImageText() {
  const banks: Bank[] = [
    { bin: 'NOVA', shortName: 'NovaBank', name: 'NovaBank (simulated)', code: 'NVB', logo: '' },
    { bin: 'DEMOA', shortName: 'Demo Bank A', name: 'Demo Bank A (simulated)', code: 'DEMOA', logo: '' },
    { bin: '970436', shortName: 'Vietcombank', name: 'Ngân hàng TMCP Ngoại Thương Việt Nam', code: 'VCB', logo: '' },
    { bin: '970422', shortName: 'MBBank', name: 'Ngân hàng TMCP Quân đội', code: 'MB', logo: '' },
  ];
  assert.equal(paymentImageText('NovaBank\nACC-ALICE-001', banks).account, 'ACC-ALICE-001');
  assert.equal(paymentImageText('Ngân hàng: Demo Bank A\nSố tài khoản: 0012 3456 7890\nSố tiền: 500,000 VND', banks).bank, 'DEMOA');
  assert.equal(paymentImageText('Ngân hàng: Demo Bank A\nSố tài khoản: 0012 3456 7890', banks).account, '001234567890');
  assert.equal(paymentImageText('Số tài khoản: O01234567\nSĐT: 0912345678', banks).account, '');
  assert.equal(paymentImageText('Số tài khoản: 1234567O89', banks).account, '');
  assert.equal(paymentImageText('Số tài khoản:\n001234567890', banks).account, '001234567890');
  assert.equal(paymentImageText('123456789\n987654321', banks).account, '');
  assert.equal(paymentImageText('Ngân hàng: Unknown Bank\nAccount number: 123456789', banks).bank, '');
  assert.equal(paymentImageText('Số tiền: 500000\nNgày 07/11/2026', banks).account, '');
  assert.equal(paymentImageText('Ngân hàng: VCB\nSTK: 001234567890', banks).bank, '970436');
  assert.equal(paymentImageText('MB\nSTK: 001234567890', banks).bank, '970422');
  assert.equal(paymentImageText('remember\nSTK: 001234567890', banks).bank, '');
  console.log('PASS: image payment suggestions preserve leading zeros, require an unambiguous account and never invent a supported bank');
}
