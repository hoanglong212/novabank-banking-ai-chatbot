import { useState } from 'react';
import { Download } from 'lucide-react';
import { api } from '../../api';
import type { DemoUser } from '../../types';

export function ReceiptButton({ user, transactionId }: { user: DemoUser; transactionId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function download() {
    setBusy(true);
    setError(null);
    try {
      const url = URL.createObjectURL(await api.receipt(user, transactionId));
      const link = document.createElement('a');
      link.href = url;
      link.download = `NovaBank-${transactionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return <>
    <button className="secondary-button" disabled={busy} onClick={download}>
      <Download size={18} aria-hidden="true" /> {busy ? 'Preparing receipt…' : 'Download PDF receipt'}
    </button>
    {error && <p className="form-error" role="alert">{error}</p>}
  </>;
}
