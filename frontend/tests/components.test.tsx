import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { MessageThread } from '../src/components/chat/MessageThread';
import { ConversationList } from '../src/components/chat/ConversationList';
import { Topbar } from '../src/components/layout/Topbar';
import { ToolActivity } from '../src/components/insights/ToolActivity';
import { Composer } from '../src/components/chat/Composer';
import { Login } from '../src/components/auth/Login';
import { NavBar } from '../src/components/app/NavBar';
import { Home } from '../src/components/home/Home';
import { Activity } from '../src/components/activity/Activity';
import type { ToolEvent } from '../src/types';

const noop = () => {};
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

const nav = renderToStaticMarkup(<NavBar tab="qr" setTab={noop} user={user} logout={noop} />);
assert.match(nav, /aria-current="page"[^>]*>(?:(?!<\/button>).)*VietQR/);
assert.ok(nav.includes('aria-label="Sign out"'));
console.log('PASS: navigation marks the current tab and offers sign out');

const profile = { id: 'alice', name: 'Alice', accounts: [{ id: 'ACC-ALICE-001', balance_vnd: 12500000, currency: 'VND' }],
  transactions: [{ id: 'TX-1004', amount_vnd: 15000000, status: 'COMPLETED', description: 'Salary credit', direction: 'in' as const, date: '2026-10-20' }] };
const home = renderToStaticMarkup(<Home user={user} profile={profile} navigate={noop} ask={noop} />);
assert.ok(!home.includes('12,500,000'), 'balance is hidden until the customer reveals it');
assert.ok(home.includes('aria-label="Show balance"') && home.includes('ACC-ALICE-001'));
assert.ok(home.includes('Salary credit') && home.includes('+15,000,000 VND'));
const loading = renderToStaticMarkup(<Home user={user} profile={null} navigate={noop} ask={noop} />);
assert.ok(loading.includes('skeleton-balance'));
const activityPage = renderToStaticMarkup(<Activity profile={profile} ask={noop} />);
assert.ok(activityPage.includes('Money in') && activityPage.includes('+15,000,000 VND') && activityPage.includes('20 October'));
console.log('PASS: balance hidden by default, skeleton while loading, activity grouped by day');

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

const qrThread = renderToStaticMarkup(<MessageThread busy={false} messages={[{ ...messages[0], content:
  'Done.\n\n![VietQR](https://img.vietqr.io/image/970436-0123456789-compact.png?amount=50000)\n![VietQR](https://evil.example/x.png)' }]} />);
assert.ok(qrThread.includes('<img src="https://img.vietqr.io/image/970436-0123456789-compact.png?amount=50000"'));
assert.equal(qrThread.match(/<img/g)?.length, 1);
assert.ok(qrThread.includes('![VietQR](https://evil.example/x.png)'));
console.log('PASS: VietQR image renders only from the VietQR image service');
