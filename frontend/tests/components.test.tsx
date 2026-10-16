import assert from 'node:assert/strict';
import { renderToStaticMarkup } from 'react-dom/server';
import { MessageThread } from '../src/components/chat/MessageThread';
import { Sidebar } from '../src/components/layout/Sidebar';
import { Topbar } from '../src/components/layout/Topbar';
import { PolicyTest } from '../src/components/insights/PolicyTest';
import { ToolActivity } from '../src/components/insights/ToolActivity';
import { Composer } from '../src/components/chat/Composer';
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

const sidebar = renderToStaticMarkup(<Sidebar user={user} busy={false} active="c1"
  sidebarOpen={false} setSidebarOpen={noop} setActive={noop}
  conversations={[{ id: 'c1', owner_id: 'alice', title: 'Private chat', created_at: '', updated_at: '' }]}
  startConversation={noop} deleteConversation={noop} />);
assert.ok(sidebar.includes('aria-current="page"'));
assert.ok(sidebar.includes('Delete conversation Private chat'));
assert.ok(sidebar.includes('Alice'));
console.log('PASS: navigation selection, identity and accessible delete label');

const header = renderToStaticMarkup(<Topbar user={user} users={[user]} busy health={null}
  title="Nova Assistant" sidebarOpen={false} setSidebarOpen={noop}
  policyPanelOpen={false} setPolicyPanelOpen={noop} changeUser={noop} />);
assert.ok(header.includes('Connecting'));
assert.match(header, /<select[^>]*disabled/);
console.log('PASS: connection status and disabled identity switch while busy');

for (const decision of ['ALLOW', 'DENY'] as const) {
  const policy = renderToStaticMarkup(<PolicyTest user={user} busy={false}
    toolName="get_account_balance" setToolName={noop} accountId="ACC-ALICE-001"
    setAccountId={noop} setPolicyResult={noop} runPolicyDryRun={noop}
    policyResult={{ decision, reason_code: 'LOCAL_POLICY_RESULT', executed: false }} />);
  assert.ok(policy.includes(decision === 'ALLOW' ? 'Permission granted' : 'Permission denied'));
  assert.ok(policy.includes('ACC-ALICE-001'));
}
console.log('PASS: permission outcomes and account field');

const events: ToolEvent[] = Array.from({ length: 8 }, (_, index) => ({
  id: String(index), tool_name: `tool-${index}`, decision: 'ALLOW',
  reason_code: 'LOCAL_POLICY_APPROVED', executed: 0, arguments: {}, created_at: '',
}));
const activity = renderToStaticMarkup(<ToolActivity events={events} />);
assert.ok(!activity.includes('tool-1'));
assert.ok(activity.indexOf('tool-7') < activity.indexOf('tool-2'));
assert.equal(events[0].tool_name, 'tool-0');
console.log('PASS: activity shows latest six in reverse order without mutating input');

const composer = renderToStaticMarkup(<Composer user={user} busy={false} draft=""
  setDraft={noop} error={null} setError={noop} hasMessages={false}
  textareaRef={{ current: null }} sendMessage={noop} pickSuggestion={noop} />);
assert.match(composer, /<button[^>]*aria-label="Send message"[^>]*disabled/);
assert.ok(!composer.includes('quick-chips'));
console.log('PASS: empty draft cannot send and welcome has no duplicate quick requests');
