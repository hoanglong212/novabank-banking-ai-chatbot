import { useEffect, useState } from 'react';
import { Download, LoaderCircle } from 'lucide-react';
import { api } from '../../api';
import type { DemoUser, VietQR } from '../../types';
import { Field, Loading, useResource } from '../explore/shared';

export function ReceiveQr({ user }: { user: DemoUser }) {
  const accounts = useResource<{ items: { id: string; holder_name: string; nickname: string }[] }>(user, '/customer/accounts');
  const [qr, setQr] = useState<VietQR | null>(null);
  const [selected, setSelected] = useState('');
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const account = accounts.data?.items.find(item => item.id === selected) ?? accounts.data?.items[0];
  useEffect(() => {
    let active = true;
    setQr(null); setError('');
    if (account) {
      void api.createVietQR(user, { bank: 'NovaBank', account_no: account.id, account_name: account.holder_name })
        .then(value => { if (active) setQr(value); })
        .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Không tải được mã QR.'); });
    }
    return () => { active = false; };
  }, [user, account?.id, account?.holder_name, attempt]);
  const currentQr = qr?.account_no === account?.id ? qr : null;
  return <div className="qr-receive">
    <p className="qr-sheet-intro">Đưa mã này cho người gửi để nhận tiền vào tài khoản của bạn.</p>
    <Loading state={accounts} />
    {(accounts.data?.items.length ?? 0) > 1 && <Field label="Tài khoản nhận"><select value={account?.id ?? ''} onChange={event => setSelected(event.target.value)}>{accounts.data?.items.map(item => <option key={item.id} value={item.id}>{item.nickname || item.holder_name} · {item.id}</option>)}</select></Field>}
    {error ? <div role="alert" className="form-error">{error} <button className="link-button" onClick={() => setAttempt(value => value + 1)}>Thử lại</button></div>
      : currentQr ? <div className="qr-receive-result"><img src={currentQr.image} alt="Mã QR nhận tiền NovaBank" /><strong>{currentQr.account_name}</strong><p>NovaBank</p><small>{currentQr.account_no}</small>
      <a className="secondary-button" href={currentQr.image} download="NovaBank-demo-QR.png"><Download size={16} />Lưu ảnh QR</a>
      <details><summary>Nội dung mã QR</summary><Field label="QR text for sharing"><textarea readOnly rows={3} value={currentQr.payload} /></Field></details>
    </div> : account ? <div className="qr-receive-empty" role="status"><LoaderCircle className="qr-spin" size={28} /><p>Đang tải mã QR của bạn…</p></div>
      : !accounts.busy && !accounts.error && <p className="qr-sheet-intro">Bạn chưa có tài khoản nhận tiền.</p>}
  </div>;
}
