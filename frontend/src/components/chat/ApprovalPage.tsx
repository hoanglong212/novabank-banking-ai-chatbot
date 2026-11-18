import { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { request } from '../../api';
import type { DemoUser } from '../../types';
import { navigate } from '../../router';
import { ApprovalEvidence, type ReviewEvidence } from './ApprovalEvidence';
import { TransferOverview } from '../transfer/TransferOverview';

interface Approval { id: string; name: string; status: string; arguments: Record<string, string | number>; expires_at: number; review?: ReviewEvidence }
export function ApprovalPage({ user, id, openTransfer }: { user: DemoUser; id: string; openTransfer: (id: string, conversation?: string) => void }) {
  const [approval, setApproval] = useState<Approval | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    request<Approval>('/agent/approvals/' + encodeURIComponent(id), user).then(value => { if (alive) setApproval(value); })
      .catch(e => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [id, user]);
  async function decide(approve: boolean) {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const result = await request<{ draft_id?: string; conversation_id?: string; message: string }>('/agent/approvals/' + encodeURIComponent(id), user,
        { method: 'POST', body: JSON.stringify({ approve }) });
      if (result.draft_id) openTransfer(result.draft_id, result.conversation_id);
      else { setApproval(previous => previous && ({ ...previous, status: approve ? 'APPROVED' : 'DECLINED' })); }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  if (approval?.name === 'prepare_transfer') {
    const fields = approval.arguments;
    const expired = approval.expires_at * 1000 < Date.now();
    return <div className="page transfer-review-page service-stack">
      <h1 className="page-title">Review your transfer</h1>
      <p className="muted">Check the amount and recipient Nova picked up from your message.</p>
      <section className="card service-section transfer-review-card">
        <TransferOverview amount={Number(fields.amount_vnd)} from={fields.from_account ? String(fields.from_account) : undefined}
          to={String(fields.to_account)} bank={String(fields.to_bank || 'NovaBank')} memo={fields.content ? String(fields.content) : undefined} />
        {approval.review?.warning && <p className="form-error" role="note">{approval.review.warning}</p>}
        {approval.review && <details className="transfer-review-evidence"><summary>Bank review checks</summary>
          <ApprovalEvidence review={{ ...approval.review, warning: '' }} />
        </details>}
        <p className="transfer-review-next"><ShieldCheck size={18} aria-hidden="true" />Your payment starts only after you confirm it in the bank verification screen.</p>
        {error && <p role="alert" className="form-error">{error}</p>}
        {approval.status === 'PENDING' ? <div className="inline-actions">
          <button className="primary-button" disabled={busy || expired} onClick={() => void decide(true)}>{busy ? 'Opening verification…' : 'Continue to verification'}</button>
          <button className="secondary-button" disabled={busy} onClick={() => void decide(false)}>Decline</button>
        </div> : <button className="secondary-button" onClick={() => navigate('/assistant')}>Back to Assistant</button>}
        {expired && approval.status === 'PENDING' && <p role="status">This transfer review expired. Ask Nova to prepare a new one.</p>}
      </section>
    </div>;
  }
  return <div className="page"><h1 className="page-title">Review assistant proposal</h1>
    <p>Approval creates a draft. Payments still require a separate verification code.</p>
    {error && <p role="alert" className="form-error">{error}</p>}
    {approval && <section className="card service-section"><h2>{approval.review?.title ?? approval.name.replaceAll('_', ' ')}</h2>
      <ApprovalEvidence review={approval.review} />
      <dl className="detail-list">{Object.entries(approval.arguments).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl>
      <p>{approval.status}</p>
      {approval.status === 'PENDING' && <div className="inline-actions">
        <button className="primary-button" disabled={busy || approval.expires_at * 1000 < Date.now()} onClick={() => void decide(true)}>Approve proposal</button>
        <button className="secondary-button" disabled={busy} onClick={() => void decide(false)}>Decline</button>
      </div>}
    </section>}
  </div>;
}
