import { useEffect, useRef, useState } from 'react';
import { FileText, Trash2, Upload } from 'lucide-react';
import { request } from '../../api';
import type { DemoUser } from '../../types';
import { Field } from './shared';
import { ConfirmRemove, EmptyState, ServiceHeading } from './ServiceUi';

type Document = {
  id: string; filename_display: string; size_bytes: number;
  status: 'processing' | 'ready' | 'quarantined' | 'scan_failed' | 'rejected';
  status_reason: string | null;
};
const labels = { processing: 'Processing', ready: 'Ready', quarantined: 'Unavailable for chat', scan_failed: 'Check interrupted', rejected: 'Not supported' };
const reasons: Record<string, string> = {
  SOURCE_INJECTION: 'This document contains instructions aimed at the assistant.',
  SOURCE_GUARD_UNAVAILABLE: 'We could not complete the safety check. Upload the same file to try again.',
  DOCUMENT_PROCESSING_UNAVAILABLE: 'We could not finish processing. Upload the same file to try again.',
  FILE_TOO_LARGE: 'Choose a file up to 5 MB.', TOO_MANY_PAGES: 'Choose a PDF with up to 50 pages.',
  TOO_MANY_CHUNKS: 'This document is too long. Upload a shorter version.',
  ENCRYPTED_PDF: 'Remove the PDF password before uploading.', INVALID_PDF: 'This PDF could not be read.',
  NO_TEXT: 'No readable text was found. Scanned documents are not supported.',
  UNSUPPORTED_FILE: 'Choose a text-based PDF, TXT or Markdown file.',
};

export function Documents({ user, ask }: { user: DemoUser; ask: (text: string) => void }) {
  const [items, setItems] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [removing, setRemoving] = useState<Document | null>(null);
  const [revision, setRevision] = useState(0);
  const [questions, setQuestions] = useState<Record<string, string>>({});
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    request<{ items: Document[] }>('/documents', user, { signal: controller.signal })
      .then(result => { setItems(result.items); setError(''); })
      .catch(() => { if (!controller.signal.aborted) setError('Could not load your documents. Please try again.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [user, revision]);
  async function upload() {
    if (!file || busy) return;
    if (file.size > 5 * 1024 * 1024) { setError('Choose a file up to 5 MB.'); return; }
    setBusy(true); setError('');
    const body = new FormData(); body.append('file', file);
    try {
      await request<Document>('/documents', user, { method: 'POST', body });
      setFile(null); if (input.current) input.current.value = '';
      setRevision(n => n + 1);
    } catch (e) {
      const reason = e instanceof Error ? e.message : '';
      setError(reason === 'DOCUMENT_LIMIT' ? 'You can keep up to 20 documents. Remove one before uploading.'
        : reason === 'UPLOAD_RATE_LIMIT' ? 'Too many uploads. Please wait a few minutes and try again.'
        : 'Upload could not finish. Refresh the list before trying again.');
    } finally { setBusy(false); }
  }
  async function remove() {
    if (!removing || busy) return;
    setBusy(true); setError('');
    try {
      await request('/documents/' + encodeURIComponent(removing.id), user, { method: 'DELETE' });
      setRemoving(null); setRevision(n => n + 1);
    } catch { setError('Could not remove this document. Please try again.'); }
    finally { setBusy(false); }
  }
  return <div className="page service-stack">
    <ServiceHeading eyebrow="YOUR RECORDS" title="My documents">Upload a document, then ask Nova about its contents.</ServiceHeading>
    <section className="card service-section">
      <h3>Upload a document</h3>
      <p className="muted">Text-based PDF, TXT or Markdown · Up to 5 MB and 50 pages · 20 documents</p>
      <div className="service-form">
        <Field label="Choose a document"><input ref={input} type="file" accept=".pdf,.txt,.md" disabled={busy}
          onChange={event => setFile(event.target.files?.[0] ?? null)} /></Field>
        <button className="primary-button" disabled={!file || busy} onClick={() => void upload()}><Upload size={18} aria-hidden="true" />{busy && !removing ? 'Checking document…' : 'Upload document'}</button>
      </div>
      {busy && !removing && <p role="status">Your document is being checked. This may take a moment.</p>}
    </section>
    {error && <p role="alert" className="form-error">{error} <button className="link-button" onClick={() => setRevision(n => n + 1)}>Refresh list</button></p>}
    {loading ? <p role="status">Loading documents…</p> : items.length === 0
      ? <EmptyState title="Your documents, in one place">Upload an invoice, contract or statement to get started.</EmptyState>
      : <div className="service-grid">{items.map(doc => <article className="card service-section" key={doc.id}>
        <FileText size={24} aria-hidden="true" /><h3 className="preserve-lines">{doc.filename_display}</h3>
        <p className="muted">{Math.max(1, Math.ceil(doc.size_bytes / 1024))} KB · <strong>{labels[doc.status]}</strong></p>
        {doc.status !== 'ready' && <p>{doc.status === 'processing' ? 'This document is still being checked. Refresh the list shortly.' : reasons[doc.status_reason ?? ''] ?? 'This document could not be prepared for chat. Try a different file.'}</p>}
        {doc.status === 'ready' && <form className="service-form" onSubmit={event => {
          event.preventDefault();
          ask('Document ' + doc.id + ': ' + (questions[doc.id]?.trim() || 'Summarize this document.'));
        }}>
          <Field label="Ask Nova"><input aria-label={'Question about ' + doc.filename_display} maxLength={900}
            placeholder="Summarize this document" value={questions[doc.id] ?? ''}
            onChange={event => setQuestions(values => ({ ...values, [doc.id]: event.target.value }))} /></Field>
          <button className="secondary-button" type="submit" disabled={busy}>Ask about document</button>
        </form>}
        <button className="link-button" aria-label={'Delete ' + doc.filename_display} disabled={busy} onClick={() => setRemoving(doc)}><Trash2 size={16} aria-hidden="true" />Delete</button>
      </article>)}</div>}
    <ConfirmRemove title="Remove document?" open={!!removing} close={() => { if (!busy) setRemoving(null); }} busy={busy} action={() => void remove()}>
      <p>Remove <strong>{removing?.filename_display}</strong> from your documents? Nova will no longer be able to read it. Previous chat answers remain in your conversation.</p>
    </ConfirmRemove>
  </div>;
}
