import { test, expect } from './fixtures';
import { demoLogin, freshPayeeFixture } from './auth-helpers';

test('week8 bank review shows frozen sources and warns about a new recipient', async ({ page }, info) => {
  await demoLogin(page, 'alice');
  freshPayeeFixture('alice', 'ACC-BOB-001');
  const token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('novabank-session')!).token);
  const headers = { Authorization: `Bearer ${token}` };
  const conversation = await (await page.request.post('/api/conversations', { headers, data: { title: 'Week8 approval' } })).json();
  const run = await (await page.request.post('/api/agent/runs', { headers, data: { conversation_id: conversation.id, content: 'Transfer 10000 VND to ACC-BOB-001 content lunch' } })).json();
  const proposal = await (await page.request.post('/api/agent/tools', { headers: { Authorization: `Bearer ${run.delegated_token}` }, data: { name: 'prepare_transfer', arguments: { to_account: 'ACC-BOB-001', amount_vnd: 10000, content: 'lunch' } } })).json();
  expect(proposal.decision).toBe('ALLOW');
  await page.goto('/approvals/' + proposal.result.approval_id);
  await expect(page.getByRole('heading', { name: 'Review your transfer', exact: true })).toBeVisible();
  await expect(page.getByRole('note')).toContainText('New recipient');
  await page.getByText('Bank review checks', { exact: true }).click();
  await expect(page.getByLabel('Bank review checks')).toContainText('From your confirmed message');
  await expect(page.getByLabel('Bank review checks')).toContainText('Medium');
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all(document.getAnimations().filter(a => a.effect?.getComputedTiming().iterations !== Infinity).map(a => a.finished)); });
  await page.screenshot({ path: info.outputPath('week8-bank-review.png'), fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: 'Continue to verification', exact: true }).click();
  await expect(page).toHaveURL(/\/transfer\/TRF-[^/]+\/otp$/);
  await expect(page.getByRole('dialog', { name: 'Transfer money', exact: true })).toBeVisible();
});
