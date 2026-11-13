import { useState } from 'react';
import type { DemoUser } from '../../types';
import { Sheet } from '../ui/Sheet';
import { Feedback, Field, Loading, send, useOperation, useResource } from './shared';
import { EmptyState } from './ServiceUi';

interface Document { id: string; title: string; content: string; source: string; trust_level: string; status: string }
export function Knowledge({ user, manage = false }: { user: DemoUser; manage?: boolean }) {
  const state = useResource<{ items: Document[] }>(user, '/knowledge'); const op = useOperation();
  const [selected, setSelected] = useState<Document | null>(null); const [creating, setCreating] = useState(false); const [query, setQuery] = useState('');
  const editable = manage && user.permissions?.includes('settings:write');
  const matches = state.data?.items.filter(d => (d.title + ' ' + d.content).toLowerCase().includes(query.toLowerCase()));
  return <section className="card service-section"><div className="page-heading"><h2 className="card-title">{manage ? 'Knowledge library' : 'Help library'}</h2>{editable && <button className="secondary-button" onClick={() => { setSelected(null); setCreating(true); }}>Add document</button>}</div><Loading state={state} /><Feedback state={op} />
    <Field label="Find a help topic"><input type="search" placeholder="Search accounts, payments, security…" value={query} onChange={e => setQuery(e.target.value)} /></Field><ul className="service-list">{matches?.map(d => <li key={d.id}><div><strong>{d.title}</strong><small>{manage ? `${d.source} · ${d.status} · ${d.trust_level}` : d.content.slice(0, 120) + (d.content.length > 120 ? '…' : '')}</small></div><button className="secondary-button" onClick={() => setSelected(d)}>{editable ? 'Review / edit' : 'Read'}</button></li>)}</ul>{!state.busy && !state.error && !matches?.length && <EmptyState title="No matching help topic">Try a shorter search, or create a support request.</EmptyState>}
    {editable && <button className="primary-button" disabled={op.busy} onClick={() => void op.run(async () => { const result = await send<{ indexed_chunks: number; embedding_model: string }>(user, '/admin/knowledge-index'); op.setMessage(`Indexed ${result.indexed_chunks} chunks with ${result.embedding_model}.`); })}>{op.busy ? 'Building local search index…' : 'Rebuild search index'}</button>}
    <Sheet open={!!selected || creating} title={editable ? 'Knowledge document' : selected?.title ?? 'Help topic'} side="right" onClose={() => { setSelected(null); setCreating(false); }}>
      {editable ? <form key={selected?.id ?? 'new'} className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/admin/knowledge' + (selected ? '/' + selected.id : ''), Object.fromEntries(data), selected ? 'PUT' : 'POST'); setSelected(null); setCreating(false); state.reload(); op.setMessage('Document saved. Rebuild the index after publishing.'); }); }}>
        <Field label="Title"><input name="title" defaultValue={selected?.title} minLength={3} maxLength={160} required /></Field><Field label="Content"><textarea name="content" rows={12} defaultValue={selected?.content} minLength={10} maxLength={20000} required /></Field><Field label="Source / provenance"><input name="source" defaultValue={selected?.source ?? 'NovaBank policy'} maxLength={250} required /></Field><Field label="Trust level"><select name="trust_level" defaultValue={selected?.trust_level ?? 'untrusted'}><option value="untrusted">Untrusted</option><option value="approved">Approved</option></select></Field><Field label="Publication"><select name="status" defaultValue={selected?.status ?? 'DRAFT'}><option>DRAFT</option><option>PUBLISHED</option></select></Field><button className="primary-button" disabled={op.busy}>Save document</button>
      </form> : selected && <><p className="preserve-lines">{selected.content}</p><small className="muted">Source: {selected.source} · {selected.id}</small></>}
    </Sheet>
  </section>;
}
