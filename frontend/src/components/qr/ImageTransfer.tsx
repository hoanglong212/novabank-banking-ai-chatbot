import { useEffect, useRef, useState } from 'react';
import { ImagePlus, ArrowUpRight, RefreshCw, LoaderCircle } from 'lucide-react';
import type { Bank, DemoUser, TransferStart } from '../../types';
import { Field, Loading, useResource } from '../explore/shared';
import { recognizeBankImage } from './recognizeBankImage';
import { paymentImageText } from './paymentImageText';

export function ImageTransfer({ user, onReview }: { user: DemoUser; onReview: (start: TransferStart) => void }) {
  const banks = useResource<Bank[]>(user, '/vietqr/banks');
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [error, setError] = useState('');
  const [bank, setBank] = useState('');
  const [account, setAccount] = useState('');
  const [reading, setReading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [notice, setNotice] = useState('');
  const [checked, setChecked] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!file || !banks.data) return;
    const task = new AbortController(); controller.current = task;
    setReading(true); setProgress(0); setError(''); setNotice(''); setChecked(false);
    void recognizeBankImage(file, task.signal, setProgress).then(result => {
      if (task.signal.aborted) return;
      const found = paymentImageText(result.text, banks.data!);
      setBank(found.bank); setAccount(found.account);
      const hints = [];
      if (!found.bank) hints.push(found.bankHint ? `Ngân hàng “${found.bankHint}” chưa khớp với danh sách hỗ trợ. Hãy kiểm tra và chọn ngân hàng.` : 'Chưa xác định được ngân hàng. Hãy chọn theo ảnh.');
      if (found.candidates.length > 1) hints.push('Ảnh có nhiều số tài khoản. Hãy nhập đúng tài khoản cần chuyển.');
      else if (!found.account) hints.push('Chưa đọc rõ số tài khoản. Bạn có thể nhập lại từ ảnh.');
      if (result.confidence < 70) hints.push('Ảnh chưa rõ, hãy đối chiếu kỹ từng chữ số.');
      setNotice(hints.join(' ') || 'Đã đọc thông tin từ ảnh. Hãy đối chiếu ngân hàng và từng chữ số trước khi tiếp tục.');
    }).catch(reason => {
      if (!task.signal.aborted) setError(reason instanceof Error ? reason.message : 'Không đọc được ảnh. Hãy thử lại hoặc nhập thông tin bên dưới.');
    }).finally(() => { if (!task.signal.aborted) setReading(false); });
    return () => { task.abort(); if (controller.current === task) controller.current = null; };
  }, [file, banks.data, attempt]);
  function cancelReading() {
    controller.current?.abort(); setReading(false);
    setNotice('Đã dừng đọc ảnh. Bạn có thể nhập thông tin bên dưới.');
  }
  function choose(value?: File) {
    if (!value) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(value.type)) { setError('Chọn ảnh PNG, JPG hoặc WebP.'); return; }
    if (value.size > 8 * 1024 * 1024) { setError('Chọn ảnh nhỏ hơn 8 MB.'); return; }
    controller.current?.abort(); setError(''); setFile(value); setBank(''); setAccount(''); setChecked(false); setNotice('');
  }
  return <div className="qr-image-transfer">
    <p className="qr-sheet-intro">Dùng ảnh có tên ngân hàng và số tài khoản. Thông tin sẽ được đưa vào bản nháp để bạn kiểm tra.</p>
    <input ref={input} tabIndex={-1} className="qr-file-input" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Ảnh thông tin tài khoản" onChange={event => { choose(event.target.files?.[0]); event.target.value = ''; }} />
    {preview ? <div className="qr-image-preview"><img src={preview} alt="Ảnh thông tin tài khoản đã chọn" /><button className="secondary-button" onClick={() => input.current?.click()}><RefreshCw size={16} />Đổi ảnh</button></div>
      : <button className="qr-image-drop" onClick={() => input.current?.click()} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); choose(event.dataTransfer.files[0]); }}><ImagePlus size={34} strokeWidth={1.5} /><strong>Chọn ảnh thông tin tài khoản</strong><span>PNG, JPG hoặc WebP · Tối đa 8 MB</span></button>}
    {error && <p role="alert" className="form-error">{error}</p>}
    {file && <>
      {reading ? <div className="qr-ocr-status"><div role="status"><LoaderCircle className="qr-spin" size={18} /><span>{progress ? `Đang đọc thông tin · ${progress}%` : 'Đang chuẩn bị bộ đọc ảnh…'}</span></div><progress aria-label="Tiến độ đọc ảnh" max={100} value={progress} /><button type="button" className="link-button" onClick={cancelReading}>Dừng và nhập thủ công</button></div>
        : <div className="qr-ocr-status"><p role="status">{notice}</p><button type="button" className="link-button" disabled={!banks.data} onClick={() => setAttempt(value => value + 1)}><RefreshCw size={14} />Đọc lại ảnh</button></div>}
      <p className="qr-ocr-private">Ảnh được đọc ngay trên thiết bị của bạn.</p>
      <form className="service-form" onSubmit={event => { event.preventDefault(); if (!reading && checked) onReview({ to_bank: bank.trim(), to_account: account.trim() }); }}>
      <Loading state={banks} />
      <Field label="Ngân hàng"><select disabled={reading} value={bank} onChange={event => { setBank(event.target.value); setChecked(false); }} required><option value="">Chọn ngân hàng</option>{banks.data?.map(item => <option key={item.bin} value={item.shortName === 'NovaBank' ? 'NovaBank' : item.bin}>{item.shortName}</option>)}</select></Field>
      <Field label="Số tài khoản"><input disabled={reading} value={account} onChange={event => { setAccount(event.target.value); setChecked(false); }} required maxLength={40} pattern={bank === 'NovaBank' ? 'ACC-[A-Z0-9-]{3,30}' : '[0-9]{6,19}'} autoComplete="off" /></Field>
      <label className="qr-ocr-confirm"><input type="checkbox" checked={checked} disabled={reading || !bank || !account} required onChange={event => setChecked(event.target.checked)} /><span>Tôi đã đối chiếu ngân hàng và số tài khoản với ảnh.</span></label>
      <button className="primary-button" disabled={reading || !checked || !bank.trim() || !account.trim()}>Kiểm tra chuyển tiền<ArrowUpRight size={17} /></button>
    </form></>}
  </div>;
}
