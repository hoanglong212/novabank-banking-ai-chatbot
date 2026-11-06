import { useEffect, useState } from 'react';
import { request } from '../../api';
import type { DemoUser } from '../../types';
import { navigate } from '../../router';

interface Approval { id: string; name: string; status: string; arguments: Record<string, string | number>; expires_at: number }
export function ApprovalPage({ user, id }: { user: DemoUser; id: string }) {
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
      const result = await request<{ draft_id?: string; message: string }>('/agent/approvals/' + encodeURIComponent(id), user,
        { method: 'POST', body: JSON.stringify({ approve }) });
      if (result.draft_id) navigate('/transfer/' + encodeURIComponent(result.draft_id) + '/otp');
      else { setApproval(previous => previous && ({ ...previous, status: approve ? 'APPROVED' : 'DECLINED' })); }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <div className="page"><h1 className="page-title">Review assistant proposal</h1>
    <p>Approval creates a draft. Payments still require a separate verification code.</p>
    {error && <p role="alert" className="form-error">{error}</p>}
    {approval && <section className="card service-section"><h2>{approval.name.replaceAll('_', ' ')}</h2>
      <dl className="detail-list">{Object.entries(approval.arguments).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value)}</dd></div>)}</dl>
      <p>{approval.status}</p>
      {approval.status === 'PENDING' && <div className="inline-actions">
        <button className="primary-button" disabled={busy || approval.expires_at * 1000 < Date.now()} onClick={() => void decide(true)}>Approve proposal</button>
        <button className="secondary-button" disabled={busy} onClick={() => void decide(false)}>Decline</button>
      </div>}
    </section>}
  </div>;
}
