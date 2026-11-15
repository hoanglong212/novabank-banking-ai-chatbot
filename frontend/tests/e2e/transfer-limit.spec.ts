import { test, expect } from './fixtures';
import { demoLogin, enterTransactionPin } from './auth-helpers';

test('customer transfer cap changes only after assistant review and bank verification', async ({ page }, info) => {
  await demoLogin(page, 'alice');
  const access = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const headers = { Authorization: 'Bearer ' + access };
  const conversation = await (await page.request.post('/api/conversations', { headers, data: { title: 'Personal transfer limit' } })).json();
  const grant = await (await page.request.post('/api/agent/runs', { headers, data: { conversation_id: conversation.id, content: 'Set my transfer limit to 100000 VND' } })).json();
  const delegated = { Authorization: 'Bearer ' + grant.delegated_token };
  const proposal = await (await page.request.post('/api/agent/tools', { headers: delegated, data: { name: 'prepare_transfer_limit', arguments: { limit_vnd: 100000 } } })).json();
  expect(proposal.decision).toBe('ALLOW');
  await page.request.post('/api/agent/finish', { headers: delegated, data: { answer: 'Please review the proposed limit.', latency_ms: 1 } });
  await page.goto('/assistant');
  await expect(page.getByRole('heading', { name: 'Review your transfer limit', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Review and approve', exact: true }).click();
  await enterTransactionPin(page, 'alice');
  await page.getByRole('button', { name: 'Confirm action', exact: true }).click();
  await expect(page.getByText('Your transfer limit was updated.', { exact: true })).toBeVisible();
  const over = await page.request.post('/api/transfers', { headers, data: { to_account: 'ACC-BOB-001', amount_vnd: 100001 } });
  expect(over.status()).toBe(400);
  expect((await over.json()).detail).toBe('PERSONAL_TRANSFER_LIMIT');
  await page.screenshot({ path: info.outputPath('transfer-limit-confirmed.png'), fullPage: true });
});
