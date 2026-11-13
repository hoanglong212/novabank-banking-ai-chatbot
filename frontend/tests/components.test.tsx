import assert from 'node:assert/strict';
import { checkPaymentImageText } from './payment-image.test';
import { loanSchedule } from '../src/calculators';
import { renderToStaticMarkup } from 'react-dom/server';
import { MessageThread } from '../src/components/chat/MessageThread';
import { ConversationList } from '../src/components/chat/ConversationList';
import { Topbar } from '../src/components/layout/Topbar';
import { ToolActivity } from '../src/components/insights/ToolActivity';
import { Composer } from '../src/components/chat/Composer';
import { Login } from '../src/components/auth/Login';
import { checkSessionCoordination } from './session.test';
import { checkOutboxOpener } from './outbox.test';
import { acceptSession, clearSession, currentSession } from '../src/sessionStore';
import { AuthFlow } from '../src/components/auth/AuthFlow';
import { parseAuthLink } from '../src/components/auth/authLink';
import { NavBar } from '../src/components/app/NavBar';
import { Home } from '../src/components/home/Home';
import { Activity, MonthCard } from '../src/components/activity/Activity';
import type { ToolEvent } from '../src/types';
import { api } from '../src/api';
import { vnd } from '../src/format';
import { ReceiptButton } from '../src/components/activity/ReceiptButton';
import { pickRange } from '../src/components/activity/TransactionFilters';
checkPaymentImageText();
checkOutboxOpener();
import { TransactionInfo } from '../src/components/activity/TransactionDetails';

{
  const zero = loanSchedule(1000000, 3, 0);
  assert.equal(zero.at(-1)?.remaining, 0);
  assert.equal(zero.reduce((n, r) => n + r.payment, 0), 1000000);
  assert.equal(zero.reduce((n, r) => n + r.interest, 0), 0);
  const interest = loanSchedule(10000000, 12, 10);
  assert.equal(interest[0].payment, 879159);
  assert.equal(interest.at(-1)?.remaining, 0);
  assert.equal(interest.reduce((n, r) => n + r.principal, 0), 10000000);
  assert.ok(interest.every(r => r.remaining >= 0 && Number.isInteger(r.payment)));
  console.log('PASS: loan schedule rounds integer VND, preserves principal and closes the final balance');
}

const noop = () => {};
assert.equal(vnd(12500000), '12,500,000 VND');
console.log('PASS NF-07: English VND separators retained by specification decision');
const user = { id: 'alice', name: 'Alice', token: 'demo' };
const messages = [{ id: '1', conversation_id: 'c1', role: 'assistant' as const,
  content: '**8,750,000 VND** <img src=x onerror=alert(1)>', created_at: '2026-10-17T12:00:00Z' }];
const thread = renderToStaticMarkup(<MessageThread messages={messages} busy />);
assert.ok(thread.includes('<strong>8,750,000 VND</strong>'));
assert.ok(thread.includes('&lt;img'));
assert.ok(!thread.includes('<img'));
assert.ok(thread.includes('Nova is typing'));
console.log('PASS: message emphasis, HTML escaping and busy indicator');

const history = renderToStaticMarkup(<ConversationList busy={false} active="c1" open={noop}
  conversations={[{ id: 'c1', owner_id: 'alice', title: 'Private chat', created_at: '', updated_at: '' }]}
  startConversation={noop} deleteConversation={noop} />);
assert.ok(history.includes('aria-current="page"'));
assert.ok(history.includes('Delete conversation Private chat'));
console.log('PASS: conversation selection and accessible delete label');

const header = renderToStaticMarkup(<Topbar health={null} busy={false} title="Nova assistant"
  openHistory={noop} openLog={noop} startConversation={noop} />);
assert.ok(header.includes('Connecting'));
assert.ok(header.includes('aria-label="Conversation history"') && header.includes('aria-label="Security log"'));
console.log('PASS: chat header shows status and opens history and security log');

const login = renderToStaticMarkup(<Login onLogin={async () => {}} notice="Your session has ended. Please sign in again." />);
assert.match(login, /type="password"/);
assert.match(login, /autoComplete="current-password"|autocomplete="current-password"/);
assert.ok(login.includes('Your session has ended'));
console.log('PASS: sign-in form masks the password and shows session notices');

const recoveryToken = 'a'.repeat(43);
assert.deepEqual(parseAuthLink('#reset-password?token=' + recoveryToken), { mode: 'reset', token: recoveryToken });
assert.deepEqual(parseAuthLink('#verify-email?token=<script>'), { mode: 'verify', token: '' });
assert.equal(parseAuthLink('#unrelated'), null);
const recoveryForm = renderToStaticMarkup(<AuthFlow onLogin={async () => { throw new Error('Not used by rendering'); }} onVerified={noop} notice={null} link={{ mode: 'reset', token: recoveryToken }} />);
assert.ok(recoveryForm.includes('autoComplete="new-password"') && recoveryForm.includes('minLength="15"'));
assert.ok(recoveryForm.includes('Confirm password') && !recoveryForm.includes(recoveryToken));
assert.ok(login.includes('Forgot password?') && login.includes('Create an account') && login.includes('Verify your email'));
console.log('PASS: account recovery entry points, bounded fragment parsing and masked new passwords without token markup');

const nav = renderToStaticMarkup(<NavBar tab="explore" setTab={noop} user={user} logout={noop} />);
assert.match(nav, /aria-current="page"[^>]*>(?:(?!<\/button>).)*Explore/);
assert.ok(nav.includes('aria-label="Sign out"'));
assert.ok(nav.includes('aria-label="Activity"'), 'icon-only tablet navigation retains accessible names');
console.log('PASS: navigation marks the current tab and offers sign out');

const profile = { id: 'alice', name: 'Alice', accounts: [{ id: 'ACC-ALICE-001', balance_vnd: 12500000, currency: 'VND' }],
  transactions: [{ id: 'TX-1004', amount_vnd: 15000000, status: 'COMPLETED', description: 'Salary credit', direction: 'in' as const, date: '2026-10-20' }] };
const home = renderToStaticMarkup(<Home user={user} profile={profile} navigate={noop} ask={noop} />);
assert.ok(!home.includes('12,500,000'), 'balance is hidden until the customer reveals it');
assert.ok(home.includes('aria-label="Show balance"') && home.includes('ACC-ALICE-001'));
// Recent transactions live on Activity now; Home is balance, actions and services.
assert.ok(!home.includes('Salary credit') && home.includes('All services') && home.includes('Search services or ask Nova'));
const loading = renderToStaticMarkup(<Home user={user} profile={null} navigate={noop} ask={noop} />);
assert.ok(loading.includes('skeleton-balance'));
const activityPage = renderToStaticMarkup(<Activity user={user} profile={profile} openTransaction={noop} />);
assert.ok(activityPage.includes('Money in') && activityPage.includes('+15,000,000 VND') && activityPage.includes('20 October'));
const totals = renderToStaticMarkup(<MonthCard profile={{ ...profile, transactions: [...profile.transactions,
  { id: 'pending', amount_vnd: 9999000, direction: 'out', status: 'PENDING', description: 'Not posted', date: '2026-10-25' }] }} />);
assert.ok(totals.includes('Completed activity') && !totals.includes('9,999,000'), 'summary must not call pending payments completed money movement or claim an unfiltered month');
assert.deepEqual(pickRange('', '', '2026-11-05'), ['2026-11-05', '']);
assert.deepEqual(pickRange('2026-11-05', '', '2026-11-09'), ['2026-11-05', '2026-11-09']);
assert.deepEqual(pickRange('2026-11-05', '', '2026-11-01'), ['2026-11-01', '2026-11-05'], 'an earlier second tap swaps the ends');
assert.deepEqual(pickRange('2026-11-01', '2026-11-05', '2026-11-20'), ['2026-11-20', ''], 'a tap after a full range starts a new one');
console.log('PASS: balance hidden by default, skeleton while loading, activity grouped by day, date range picking');

const events: ToolEvent[] = Array.from({ length: 8 }, (_, index) => ({
  id: String(index), tool_name: `tool-${index}`, decision: 'ALLOW',
  reason_code: 'LOCAL_POLICY_APPROVED', executed: 0, arguments: {}, created_at: '',
}));
const activity = renderToStaticMarkup(<ToolActivity events={events} />);
assert.ok(!activity.includes('tool-1'));
assert.ok(activity.indexOf('tool-7') < activity.indexOf('tool-2'));
assert.equal(events[0].tool_name, 'tool-0');
const blocked = renderToStaticMarkup(<ToolActivity events={[{ ...events[0], tool_name: 'get_account_balance', decision: 'DENY', reason_code: 'ACCOUNT_NOT_OWNED' }]} />);
assert.ok(blocked.includes('Balance check') && blocked.includes('Not your account') && blocked.includes('Blocked'));
console.log('PASS: security log shows the latest six in plain language');

const composer = renderToStaticMarkup(<Composer user={user} busy={false} draft=""
  setDraft={noop} error={null} setError={noop} hasMessages={false}
  textareaRef={{ current: null }} sendMessage={noop} pickSuggestion={noop} />);
assert.match(composer, /<button[^>]*aria-label="Send message"[^>]*disabled/);
assert.ok(!composer.includes('quick-chips'));
console.log('PASS: empty draft cannot send and welcome has no duplicate quick requests');

const workingComposer = renderToStaticMarkup(<Composer user={user} busy draft=""
  setDraft={noop} error={null} setError={noop} hasMessages={true}
  textareaRef={{ current: null }} sendMessage={noop} pickSuggestion={noop} />);
assert.ok(workingComposer.includes('aria-label="Stop response"'));
console.log('PASS AI-12: busy composer exposes Stop response');

const qrThread = renderToStaticMarkup(<MessageThread busy={false} messages={[{ ...messages[0], content:
  'Done.\n\n![VietQR](data:image/png;base64,iVBORw0KGgo=)\n![VietQR](https://evil.example/x.png)' }]} />);
assert.ok(qrThread.includes('<img src="data:image/png;base64,iVBORw0KGgo="'));
assert.equal(qrThread.match(/<img/g)?.length, 1);
assert.ok(qrThread.includes('![VietQR](https://evil.example/x.png)'));
console.log('PASS: demo QR renders only inline PNGs and blocks external images');

for (const id of ['TRF-1234ABCD', 'TRF-1234567890ABCDEF1234567890ABCDEF']) {
  const transferMessage = renderToStaticMarkup(<MessageThread busy={false} openTransfer={noop}
    messages={[{ ...messages[0], content: `Transfer draft ${id}. Nothing has been sent yet.` }]} />);
  assert.ok(transferMessage.includes('Review &amp; confirm'), `draft ${id} must open the confirmation flow`);
}
console.log('PASS: chat can open both legacy and full-length transfer drafts');

const completed = { ...profile.transactions[0], account_id: 'ACC-ALICE-001', holder_name: 'ALICE NGUYEN',
  balance_after_vnd: 8000000, counterparty_name: '<img src=x>', counterparty_account: 'ACC-BOB-001' };
const details = renderToStaticMarkup(<TransactionInfo transaction={completed} />);
assert.ok(details.includes('8,000,000 VND') && details.includes('TX-1004'));
assert.ok(details.includes('&lt;img') && !details.includes('<img'));
const legacy = renderToStaticMarkup(<TransactionInfo transaction={{ ...completed, balance_after_vnd: null }} />);
assert.ok(legacy.includes('Not recorded'));
assert.ok(renderToStaticMarkup(<ReceiptButton user={user} transactionId="TX-1004" />).includes('Download PDF receipt'));
const staffNav = renderToStaticMarkup(<NavBar tab="admin" setTab={noop} logout={noop}
  user={{ ...user, id: 'admin', role: 'admin', permissions: ['admin:transactions:read'] }} />);
assert.ok(staffNav.includes('Operations') && !staffNav.includes('VietQR') && !staffNav.includes('Assistant'));
assert.ok(renderToStaticMarkup(<NavBar tab="notifications" setTab={noop} user={user} logout={noop} />).includes('Alerts'));
console.log('PASS: recorded balances, escaped details, PDF action and role-specific navigation');

async function checkTransferRetry() {
  acceptSession({ access_token: 'demo', refresh_token: 'refresh', session_id: 'session-alice', expires_in: 300,
    idle_expires_at: Date.now() / 1000 + 300, absolute_expires_at: Date.now() / 1000 + 28800,
    user: { id: 'alice', name: 'Alice', role: 'customer', permissions: [] } });
  const user = currentSession()!.user;
  const originalFetch = globalThis.fetch;
  const calls: RequestInit[] = [];
  globalThis.fetch = async (_url, options) => {
    calls.push(options!);
    if (calls.length === 1) throw new TypeError('Simulated lost response');
    return new Response(JSON.stringify({ id: 'TRF-ONE', status: 'COMPLETED' }));
  };
  try {
    await assert.rejects(api.confirmTransfer(user, 'TRF-ONE', '123456', 'stable-request-key'));
    const receipt = await api.confirmTransfer(user, 'TRF-ONE', '123456', 'stable-request-key');
    assert.equal(receipt.status, 'COMPLETED');
    assert.equal(calls.length, 2);
    for (const call of calls) {
      const headers = new Headers(call.headers);
      assert.equal(headers.get('Idempotency-Key'), 'stable-request-key');
      assert.equal(headers.get('Authorization'), 'Bearer demo');
      assert.deepEqual(JSON.parse(String(call.body)), { otp: '123456' });
    }
    console.log('PASS: transfer API retains the idempotency key after a lost response');
  } finally {
    globalThis.fetch = originalFetch;
    clearSession();
  }
}
void (async () => { await checkTransferRetry(); await checkSessionCoordination(); })().catch(error => { console.error(error); process.exitCode = 1; });
