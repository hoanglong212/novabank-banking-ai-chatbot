import { useEffect, useState } from 'react';
import type { DemoUser } from '../../types';
import { streamMessage } from '../../api';
import { download, Feedback, Field, Loading, send, useOperation, useResource } from './shared';
import { Sheet } from '../ui/Sheet';
import { Paperclip, Plus, RefreshCw, Send, Sparkles, UserRound } from 'lucide-react';
import { EmptyState, ServiceHeading, displayDate } from './ServiceUi';
import '../../styles/support.css';

interface Ticket { id: string; subject: string; description: string; status: string; created_at: string; owner_id: string; assigned_to: string | null; category?: string }
interface Detail extends Ticket { messages: { id: string; author_id: string; body: string; created_at: string }[]; attachments: { id: string; name: string; size_bytes: number }[] }
interface Proposal { id: string; name: string; status: string; arguments: Record<string, string> }

const STATUSES = [['', 'All'], ['OPEN', 'Open'], ['IN_PROGRESS', 'In progress'], ['RESOLVED', 'Resolved'], ['CLOSED', 'Closed']] as const;
const statusLabel = (s: string) => STATUSES.find(([k]) => k === s)?.[1] ?? s;
const when = (iso: string) => new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

function StatusPill({ status }: { status: string }) {
  return <span className={'ticket-pill is-' + status.toLowerCase()}>{statusLabel(status)}</span>;
}

export function Support({ user, ticket }: { user: DemoUser; ticket?: string }) {
  const staff = user.permissions?.includes('support:write'); const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState(''), [creating, setCreating] = useState(false);
  const state = useResource<{ items: Ticket[]; total: number }>(user, '/support/tickets?offset=' + offset + (status ? '&status=' + status : ''));
  const [selected, setSelected] = useState<string | null>(ticket ?? null); const op = useOperation();
  return <div className="service-stack support-page">
    <ServiceHeading eyebrow={staff ? 'SUPPORT DESK' : 'LET’S WORK IT OUT'} title={staff ? 'Support inbox' : 'A helping hand, when you need one'}
      action={!staff && <button className="primary-button" onClick={() => setCreating(true)}><Plus size={17} />New support request</button>}>
      {staff ? 'Open a ticket to read the conversation, reply, or let Nova draft the answer for you.' : 'Ask a question, share a document and follow the conversation.'}
    </ServiceHeading>
    <div className="ticket-toolbar">
      <div className="ticket-filters" role="group" aria-label="Ticket status">{STATUSES.map(([key, label]) =>
        <button key={key} className="ticket-filter" aria-pressed={status === key} onClick={() => { setStatus(key); setOffset(0); }}>{label}</button>)}</div>
      <button className="secondary-button" onClick={state.reload}><RefreshCw size={15} aria-hidden="true" />Refresh</button>
    </div>
    <Loading state={state} /><Feedback state={{ error: creating ? '' : op.error, message: op.message }} />
    <ul className="ticket-list">{state.data?.items.map(t => <li key={t.id}>
      <button className="ticket-row" aria-label={'Open ticket ' + t.subject} onClick={() => setSelected(t.id)}>
        <span className="ticket-avatar" aria-hidden="true">{(staff ? t.owner_id : t.subject).charAt(0).toUpperCase()}</span>
        <span className="ticket-row-main">
          <span className="ticket-row-top"><strong>{t.subject}</strong><StatusPill status={t.status} /></span>
          <span className="ticket-row-preview">{t.description}</span>
          <small>{staff && <>{t.owner_id} · </>}{t.category && t.category !== 'GENERAL' && <>{t.category.toLowerCase()} · </>}{displayDate(t.created_at)} · {t.id}{t.assigned_to && <> · assigned to {t.assigned_to}</>}</small>
        </span>
      </button>
    </li>)}</ul>
    {!state.busy && !state.error && !state.data?.items.length && <EmptyState title="No tickets in this view">{staff ? 'Nothing waiting here. Choose another status to see older conversations.' : 'Create a support request or choose another status to see your conversations.'}</EmptyState>}
    {!!state.data && state.data.total > 20 && <div className="inline-actions"><button className="secondary-button" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 20))}>Previous</button><button className="secondary-button" disabled={offset + 20 >= state.data.total} onClick={() => setOffset(n => n + 20)}>Next</button></div>}
    {!staff && <Sheet open={creating} title="Start a support conversation" onClose={() => setCreating(false)}><div className="service-dialog"><p>Tell us what happened. You can add supporting files after creating your request.</p><Feedback state={op} /><form className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { const result = await send<Ticket>(user, '/support/tickets', Object.fromEntries(data)); setCreating(false); setStatus(''); setOffset(0); state.reload(); setSelected(result.id); }); }}>
      <Field label="Category"><select name="category"><option value="GENERAL">General</option><option value="PAYMENT">Payment</option><option value="CARD">Card</option><option value="ACCOUNT">Account</option><option value="SECURITY">Security</option></select></Field><Field label="Subject"><input name="subject" required minLength={3} maxLength={160} /></Field><Field label="What happened?"><textarea name="description" required minLength={5} maxLength={5000} rows={4} /></Field><button className="primary-button" disabled={op.busy}>Create ticket</button>
    </form></div></Sheet>}
    <Sheet open={!!selected} onClose={() => { setSelected(null); state.reload(); }} title="Support ticket" side="right">{selected && <TicketDetail key={selected} user={user} id={selected} />}</Sheet>
  </div>;
}

function TicketDetail({ user, id }: { user: DemoUser; id: string }) {
  const state = useResource<Detail>(user, '/support/tickets/' + id); const op = useOperation(); const staff = user.permissions?.includes('support:write');
  const [draft, setDraft] = useState('');
  const t = state.data; const closed = t?.status === 'CLOSED';
  // Poll so the other side's replies appear while the conversation is open.
  useEffect(() => { const timer = window.setInterval(() => { if (document.visibilityState === 'visible') state.reload(); }, 10_000); return () => window.clearInterval(timer); }, [state.reload]);
  const who = (author: string) => author === user.id ? 'You' : t && author === t.owner_id ? (staff ? t.owner_id : 'You') : 'NovaBank support';
  return <div className="ticket-view"><Loading state={{ ...state, busy: state.busy && !t }} /><Feedback state={op} />{t && <>
    <header className="ticket-head">
      <h3>{t.subject}</h3>
      <div className="ticket-meta"><StatusPill status={t.status} /><span>{t.id}</span>{t.category && <span>{t.category.toLowerCase()}</span>}{staff && <span><UserRound size={13} aria-hidden="true" />{t.owner_id}</span>}<span>{t.assigned_to ? 'Assigned to ' + t.assigned_to : 'Unassigned'}</span>
        <button className="link-button" onClick={state.reload}>Refresh conversation</button></div>
    </header>

    {staff && !closed && <AgentAssist user={user} ticket={t} editDraft={body => setDraft(body)} done={state.reload} />}

    <ol className="ticket-thread">
      <li className={'bubble ' + (t.owner_id === user.id ? 'is-mine' : 'is-theirs')}><span className="bubble-author">{who(t.owner_id)} · {when(t.created_at)}</span><p className="preserve-lines">{t.description}</p></li>
      {t.messages.map(m => <li key={m.id} className={'bubble ' + (m.author_id === user.id ? 'is-mine' : 'is-theirs')}><span className="bubble-author">{who(m.author_id)} · {when(m.created_at)}</span><p className="preserve-lines">{m.body}</p></li>)}
    </ol>
    {closed && <p className="service-hint">This conversation is closed. Start a new request if you need more help.</p>}

    <form className="ticket-composer" onSubmit={e => { e.preventDefault(); void op.run(async () => { await send(user, `/support/tickets/${id}/messages`, { body: draft }); setDraft(''); state.reload(); }); }}>
      <Field label="Reply"><textarea name="body" required maxLength={5000} rows={3} value={draft} onChange={e => setDraft(e.target.value)} disabled={closed} placeholder={closed ? 'Ticket closed' : 'Write a reply…'} /></Field>
      <button className="primary-button" disabled={op.busy || closed || !draft.trim()}><Send size={16} aria-hidden="true" />Send reply</button>
    </form>

    {staff && <form className="ticket-manage" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/support/tickets/' + id, { status: data.get('status'), assigned_to: data.get('assigned') || null }, 'PATCH'); state.reload(); }); }}>
      <Field label="Status"><select name="status" defaultValue={t.status}>{STATUSES.slice(1).map(([k, label]) => <option key={k} value={k}>{label}</option>)}</select></Field>
      <Field label="Assign to staff username"><input name="assigned" defaultValue={t.assigned_to ?? ''} maxLength={64} placeholder="support" /></Field>
      <button className="secondary-button" disabled={op.busy}>Update ticket</button>
    </form>}

    <section className="ticket-files"><h4><Paperclip size={15} aria-hidden="true" />Attachments</h4>
      {!!t.attachments.length && <ul className="service-list">{t.attachments.map(a => <li key={a.id}><span>{a.name} <small>({Math.ceil(a.size_bytes / 1024)} KB)</small></span><button className="link-button" disabled={op.busy} onClick={() => void op.run(async () => download(user, '/support/attachments/' + a.id, a.name))}>Download</button></li>)}</ul>}
      <Field label="Add PNG, JPEG, PDF or text (up to 2 MB)"><input type="file" accept=".png,.jpg,.jpeg,.pdf,.txt" disabled={op.busy || closed || t.attachments.length >= 5} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (!file) return; void op.run(async () => { if (file.size > 2 * 1024 * 1024) throw new Error('Choose a file smaller than 2 MB.'); const encoded = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onerror = () => reject(new Error('Unable to read this file.')); reader.onload = () => resolve(String(reader.result).split(',')[1]); reader.readAsDataURL(file); }); await send(user, `/support/tickets/${id}/attachments`, { name: file.name, content_base64: encoded }); state.reload(); }); }} /></Field>
    </section>
  </>}</div>;
}

// Nova reads the ticket and drafts the reply/status change; the bank applies them only when staff approve here.
function AgentAssist({ user, ticket, editDraft, done }: { user: DemoUser; ticket: Detail; editDraft: (body: string) => void; done: () => void }) {
  const [resolve, setResolve] = useState(true); const [progress, setProgress] = useState('');
  const [answer, setAnswer] = useState(''); const [proposals, setProposals] = useState<Proposal[] | null>(null);
  const op = useOperation();
  function handle() {
    void op.run(async () => {
      setAnswer(''); setProposals(null); setProgress('Starting…');
      const conversation = await send<{ id: string }>(user, '/conversations', { title: 'Ticket ' + ticket.id });
      // The bank only offers write proposals when the request starts with the action verb.
      const prompt = `Reply to ${ticket.id} after you read the ticket and check the customer summary for this ticket. Answer the question it asks and greet the customer with Hello` + (resolve ? ', and mark it resolved.' : '.');
      try {
        const result = await streamMessage(user, conversation.id, prompt, 'defended', setProgress);
        setAnswer(result.message?.content ?? '');
      } finally { setProgress(''); }
      const listed = await send<{ items: Proposal[] }>(user, '/agent/approvals?conversation_id=' + encodeURIComponent(conversation.id), undefined, 'GET');
      setProposals(listed.items.filter(p => p.status === 'PENDING'));
    });
  }
  function decide(p: Proposal, approve: boolean, after?: () => void) {
    void op.run(async () => {
      await send(user, '/agent/approvals/' + p.id, { approve });
      setProposals(list => (list ?? []).filter(x => x.id !== p.id)); after?.(); done();
      if (approve) op.setMessage(p.name === 'propose_ticket_reply' ? 'Reply sent to the customer.' : 'Ticket updated.');
    });
  }
  return <section className="agent-assist" aria-label="Nova assistant">
    <div className="agent-assist-head"><span className="agent-assist-icon" aria-hidden="true"><Sparkles size={18} /></span>
      <div><strong>Let Nova handle this ticket</strong><small>Nova reads the conversation, checks the customer's accounts and drafts a reply. Nothing is sent until you approve it.</small></div></div>
    {!proposals && <div className="agent-assist-actions">
      <label className="check-field"><input type="checkbox" checked={resolve} onChange={e => setResolve(e.target.checked)} />Also mark resolved</label>
      <button className="primary-button" disabled={op.busy} onClick={handle}><Sparkles size={16} aria-hidden="true" />{op.busy ? 'Nova is working…' : 'Let Nova handle it'}</button>
    </div>}
    {progress && <p role="status" className="agent-assist-progress"><span className="agent-dot" aria-hidden="true" />{progress}</p>}
    <Feedback state={op} />
    {proposals && <>
      {answer && !proposals.length && <p className="agent-assist-note">{answer}</p>}
      {!proposals.length && <p className="muted">Nova did not prepare anything to approve. <button className="link-button" onClick={() => setProposals(null)}>Try again</button></p>}
      {proposals.map(p => p.name === 'propose_ticket_reply'
        ? <div key={p.id} className="agent-draft"><span className="agent-draft-label">Draft reply</span><blockquote className="preserve-lines">{p.arguments.body}</blockquote>
            <div className="inline-actions"><button className="primary-button" disabled={op.busy} onClick={() => decide(p, true)}><Send size={15} aria-hidden="true" />Approve and send</button>
              <button className="secondary-button" disabled={op.busy} onClick={() => decide(p, false, () => editDraft(p.arguments.body))}>Edit first</button>
              <button className="link-button" disabled={op.busy} onClick={() => decide(p, false)}>Discard</button></div></div>
        : p.name === 'propose_ticket_status'
          ? <div key={p.id} className="agent-draft"><span className="agent-draft-label">Status change</span><p>Mark ticket as <StatusPill status={p.arguments.status} />{p.arguments.assigned_to && <> and assign to {p.arguments.assigned_to}</>}</p>
              {p.arguments.status === 'RESOLVED' && proposals.some(r => r.name === 'propose_ticket_reply' && r.arguments.body?.includes('?')) && <p className="service-hint">The draft asks the customer a question. You may want to skip this and keep the ticket open until they answer.</p>}
              <div className="inline-actions"><button className="primary-button" disabled={op.busy} onClick={() => decide(p, true)}>Apply</button><button className="link-button" disabled={op.busy} onClick={() => decide(p, false)}>Skip</button></div></div>
          : null)}
    </>}
  </section>;
}
