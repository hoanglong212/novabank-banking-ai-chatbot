import { useEffect, useState } from 'react';
import { Download, RefreshCw, ShieldCheck, ShieldOff } from 'lucide-react';
import type { DemoUser } from '../../types';
import { download, Feedback, Loading, send, useOperation, useResource } from '../explore/shared';

interface Bucket { runs: number; calls: number; allow: number; deny: number; error: number; deny_reasons: Record<string, number> }
interface Status { gateway: 'on' | 'off'; session: { users: string[]; expires_at: number } | null; lab: boolean; log_file: string; metrics: Record<'on' | 'off', Bucket> }
interface Entry { created_at: string; gateway: string; profile: string; owner_id: string; role: string; run_id: string; chat_request_id: string | null; tool_request_id: string | null; ordinal: number; tool: string; decision: 'ALLOW' | 'DENY' | 'ERROR'; reason: string; latency_ms: number }
const rate = (part: number, whole: number) => whole ? `${((part / whole) * 100).toFixed(1)}%` : '—';
const time = (iso: string) => new Date(iso).toLocaleTimeString('en-GB', { timeZone: 'Asia/Ho_Chi_Minh' });

// Lab switch for the agent tool gateway plus the per-call log used to compare off against on.
export function Gateway({ user }: { user: DemoUser }) {
  const status = useResource<Status>(user, '/admin/agent-gateway'); const op = useOperation();
  const [gateway, setGateway] = useState(''); const [targets, setTargets] = useState('alice, bob'); const [decision, setDecision] = useState(''); const [offset, setOffset] = useState(0);
  const query = new URLSearchParams({ limit: '50', offset: String(offset), ...(gateway && { gateway }), ...(decision && { decision }) });
  const log = useResource<{ items: Entry[]; total: number }>(user, '/admin/agent-gateway/log?' + query);
  useEffect(() => { const timer = window.setInterval(() => { if (document.visibilityState === 'visible') { status.reload(); log.reload(); } }, 5000); return () => window.clearInterval(timer); }, [status.reload, log.reload]);
  const writable = user.permissions?.includes('settings:write'); const s = status.data; const on = s?.gateway !== 'off';
  const flip = () => void op.run(async () => {
    const users = targets.split(',').map(t => t.trim()).filter(Boolean);
    await send(user, '/admin/agent-gateway', on ? { enabled: false, users, minutes: 30 } : { enabled: true }, 'PUT');
    status.reload(); op.setMessage(on ? `Gateway is OFF for ${users.join(', ')} for 30 minutes. Everyone else stays protected.` : 'Gateway is ON for everyone again.');
  });
  return <div className="service-stack">
    <section className={'card service-section gateway-switch ' + (on ? 'is-on' : 'is-off')}>
      <div className="gateway-switch-head">
        {on ? <ShieldCheck size={28} aria-hidden="true" /> : <ShieldOff size={28} aria-hidden="true" />}
        <div><h2 className="card-title">Agent gateway is {on ? 'ON' : `OFF for ${s?.session?.users.join(', ')}`}</h2>
          <p className="muted">{on ? 'Every tool call goes through role, intent and proposal checks, source screening and the two-denial stop.'
            : 'Lab mode: tool calls run with the model\'s own arguments. Sign-in, schemas, the call budget, owner-scoped data and human approval still apply.'}</p></div>
      </div>
      <Loading state={status} /><Feedback state={op} />
      {s && <div className="inline-actions">
        {writable && on && s.lab && <label className="field">Measure for users<input value={targets} onChange={e => setTargets(e.target.value)} placeholder="alice, bob" /></label>}
        {writable && <button className={on ? 'secondary-button' : 'primary-button'} disabled={op.busy || (on && !s.lab)} onClick={flip}>{on ? 'Switch gateway OFF' : 'Switch gateway ON'}</button>}
        {!s.lab && <span className="muted small">Switching off needs ENV=demo or ENV=lab on the server.</span>}
      </div>}
      <p className="muted small">OFF is a measurement session: it covers only the users listed{s?.session && <>, until {new Date(s.session.expires_at * 1000).toLocaleTimeString('en-GB', { timeZone: 'Asia/Ho_Chi_Minh' })}</>}. It applies to runs started after it changes, and each run keeps the setting it started with.{s?.log_file && <> Live log file: <code>{s.log_file}</code></>}</p>
    </section>

    {s && <section className="card service-section"><h3>Gateway off vs on</h3>
      <div className="operations-table" role="region" aria-label="Gateway comparison" tabIndex={0}><table><thead><tr><th>Measure</th><th>Gateway OFF</th><th>Gateway ON</th></tr></thead><tbody>
        <tr><td>Assistant runs</td><td>{s.metrics.off.runs}</td><td>{s.metrics.on.runs}</td></tr>
        <tr><td>Tool calls</td><td>{s.metrics.off.calls}</td><td>{s.metrics.on.calls}</td></tr>
        <tr><td>ALLOW</td><td>{s.metrics.off.allow} <small>{rate(s.metrics.off.allow, s.metrics.off.calls)}</small></td><td>{s.metrics.on.allow} <small>{rate(s.metrics.on.allow, s.metrics.on.calls)}</small></td></tr>
        <tr><td>DENY</td><td>{s.metrics.off.deny} <small>{rate(s.metrics.off.deny, s.metrics.off.calls)}</small></td><td>{s.metrics.on.deny} <small>{rate(s.metrics.on.deny, s.metrics.on.calls)}</small></td></tr>
        <tr><td>ERROR <small>(off only: call reached code that did not expect it)</small></td><td>{s.metrics.off.error}</td><td>{s.metrics.on.error}</td></tr>
        <tr><td>Top deny reasons</td>{(['off', 'on'] as const).map(g => <td key={g}>{Object.entries(s.metrics[g].deny_reasons).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([r, n]) => <div key={r}><code>{r}</code> {n}</div>)}</td>)}</tr>
      </tbody></table></div>
      <p className="muted small">Counts every agent tool call in this database. For attack success rates on a fixed scenario set, run <code>tools/gateway_compare.py</code>.</p>
    </section>}

    <section className="card service-section"><div className="gateway-log-head"><h3>Decision log</h3>
      <div className="inline-actions">
        <select aria-label="Gateway state" value={gateway} onChange={e => { setGateway(e.target.value); setOffset(0); }}><option value="">On and off</option><option value="off">Gateway off</option><option value="on">Gateway on</option></select>
        <select aria-label="Decision" value={decision} onChange={e => { setDecision(e.target.value); setOffset(0); }}><option value="">All decisions</option><option>ALLOW</option><option>DENY</option><option>ERROR</option></select>
        <button className="secondary-button" onClick={log.reload}><RefreshCw size={15} aria-hidden="true" />Refresh</button>
        <button className="secondary-button" disabled={op.busy} onClick={() => void op.run(async () => download(user, '/admin/agent-gateway/log.csv' + (gateway ? '?gateway=' + gateway : ''), 'agent-gateway-log.csv'))}><Download size={15} aria-hidden="true" />CSV</button>
      </div></div>
      <p className="muted small">Match a row to Caido/Burp with the <code>X-Request-ID</code> response header: <b>chat</b> is the user's message request, <b>tool</b> is the agent's call to <code>/api/agent/tools</code>.</p>
      <Loading state={log} />
      <div className="operations-table" role="region" aria-label="Gateway decision log" tabIndex={0}><table><thead><tr><th>Time</th><th>Gateway</th><th>User</th><th>Tool</th><th>Decision</th><th>Reason</th><th>Request IDs</th></tr></thead><tbody>
        {log.data?.items.map(e => <tr key={e.run_id + e.ordinal}><td>{time(e.created_at)}<small>{e.latency_ms} ms</small></td><td><span className={'gateway-pill is-' + e.gateway}>{e.gateway.toUpperCase()}</span><small>{e.profile}</small></td><td>{e.owner_id}<small>{e.role}</small></td><td><code>{e.tool}</code><small>#{e.ordinal}</small></td><td><span className={'gateway-pill is-' + e.decision.toLowerCase()}>{e.decision}</span></td><td><code>{e.reason}</code></td><td className="gateway-ids"><small>chat {e.chat_request_id ?? '—'}</small><small>tool {e.tool_request_id ?? '—'}</small></td></tr>)}
      </tbody></table></div>
      {log.data && !log.data.items.length && <p className="muted">No tool calls yet. Ask the assistant something, then refresh.</p>}
      <div className="inline-actions"><button className="secondary-button" disabled={!offset} onClick={() => setOffset(n => Math.max(0, n - 50))}>Previous</button><button className="secondary-button" disabled={!log.data || offset + 50 >= log.data.total} onClick={() => setOffset(n => n + 50)}>Next</button><span className="muted small">{log.data?.total ?? 0} calls</span></div>
    </section>
  </div>;
}
