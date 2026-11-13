import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, ImagePlus, QrCode, ShieldCheck, Upload, LoaderCircle } from 'lucide-react';
import type { DemoUser, TransferStart } from '../../types';
import { vnd } from '../../format';
import { Feedback, Field, send, useOperation } from '../explore/shared';
import { Sheet } from '../ui/Sheet';
import { QrCamera } from './QrCamera';
import { ReceiveQr } from './ReceiveQr';
import { ImageTransfer } from './ImageTransfer';
import { readQrFile } from './qrReader';
import '../../styles/qr-pay.css';

interface Decoded { bank: string; account_no: string; account_name?: string; amount_vnd?: number; add_info?: string }
// Shared with Nova's drop target. The server validates signed contents; images never reach the assistant.
export async function decodeQrImage(user: DemoUser, file: File) {
  return send<Decoded>(user, '/qr/decode', { payload: await readQrFile(file) });
}
export const toTransfer = (data: Decoded): TransferStart => ({ to_bank: data.bank, to_account: data.account_no, to_name: data.account_name, amount_vnd: data.amount_vnd, content: data.add_info });

export function QrStudio({ user, pay }: { user: DemoUser; pay: (start: TransferStart) => void }) {
  const [panel, setPanel] = useState<'receive' | 'image' | 'text' | null>(null);
  const [decoded, setDecoded] = useState<Decoded | null>(null);
  const [choosingFile, setChoosingFile] = useState(false);
  const upload = useRef<HTMLInputElement>(null);
  const op = useOperation();
  useEffect(() => {
    const input = upload.current;
    const cancel = () => setChoosingFile(false);
    input?.addEventListener('cancel', cancel);
    return () => input?.removeEventListener('cancel', cancel);
  }, []);
  function review(start: TransferStart) { setPanel(null); setDecoded(null); pay(start); }
  async function readPayload(payload: string) { await op.run(async () => { setDecoded(await send<Decoded>(user, '/qr/decode', { payload })); setPanel(null); }); }
  return <div className="qr-pay-page" lang="vi">
    <header className="qr-pay-heading"><div><p className="qr-pay-eyebrow">THANH TOÁN & NHẬN TIỀN</p><h1>QR Pay<span aria-hidden="true">.</span></h1></div><span className="qr-pay-bank"><ShieldCheck size={16} aria-hidden="true" />NovaBank</span></header>
    <div className="qr-pay-workspace">
      <div className="qr-pay-intro"><h2>Quét mã để chuyển tiền</h2><p>Quét mã QR để mở thông tin người nhận.</p></div>
      <QrCamera paused={!!panel || !!decoded || op.busy || choosingFile} onRead={readPayload} />
      <div className="qr-pay-feedback" aria-busy={op.busy}><Feedback state={op} />{op.busy && <p role="status"><LoaderCircle className="qr-spin" size={16} />Đang đọc mã QR…</p>}</div>
      <div className="qr-pay-actions" aria-label="Các tính năng QR Pay">
        <button disabled={op.busy} onClick={() => setPanel('receive')}><span className="qr-action-icon"><QrCode size={25} strokeWidth={1.6} /></span><span>Mã QR của tôi</span></button>
        <button disabled={op.busy} onClick={() => setPanel('image')}><span className="qr-action-icon"><ImagePlus size={25} strokeWidth={1.6} /></span><span>Chuyển tiền bằng hình ảnh</span></button>
        <button disabled={op.busy} onClick={() => { setChoosingFile(true); upload.current?.click(); }}><span className="qr-action-icon"><Upload size={25} strokeWidth={1.6} /></span><span>Tải ảnh lên</span></button>
      </div>
      <input ref={upload} tabIndex={-1} className="qr-file-input" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Upload NovaBank QR image" onChange={event => { const file = event.target.files?.[0]; event.target.value = ''; setChoosingFile(false); if (file) void op.run(async () => setDecoded(await decodeQrImage(user, file))); }} />
      <div className="qr-pay-foot"><p><ShieldCheck size={15} aria-hidden="true" />Bạn luôn kiểm tra người nhận trước khi xác nhận.</p><button onClick={() => setPanel('text')}>Dán nội dung mã QR<ArrowUpRight size={14} /></button></div>
    </div>
    <p className="qr-pay-demo">Mã QR dùng trong bản mô phỏng NovaBank.</p>
    <Sheet open={panel === 'receive'} onClose={() => setPanel(null)} title="Mã QR của tôi"><ReceiveQr user={user} /></Sheet>
    <Sheet open={panel === 'image'} onClose={() => setPanel(null)} title="Chuyển tiền bằng hình ảnh"><ImageTransfer user={user} onReview={review} /></Sheet>
    <Sheet open={panel === 'text'} onClose={() => setPanel(null)} title="Dán nội dung mã QR"><form className="service-form" onSubmit={event => { event.preventDefault(); void readPayload(String(new FormData(event.currentTarget).get('payload'))); }}>
      <p className="qr-sheet-intro">Dán nội dung mã NovaBank để xem thông tin người nhận.</p><Feedback state={op} /><Field label="QR text"><textarea name="payload" rows={4} maxLength={4000} required placeholder="NBQR1:…" /></Field><button className="primary-button" disabled={op.busy}>{op.busy ? 'Đang đọc…' : 'Đọc mã QR'}</button>
    </form></Sheet>
    <Sheet open={!!decoded} onClose={() => setDecoded(null)} title="Thông tin mã QR">{decoded && <div className="qr-decoded"><span className="qr-decoded-icon"><QrCode size={29} /></span><h3>{decoded.account_name || 'Người nhận'}</h3><p className="qr-sheet-intro">Kiểm tra thông tin trước khi mở bản nháp chuyển tiền.</p>
      <dl className="detail-list"><div><dt>Ngân hàng</dt><dd>{decoded.bank}</dd></div><div><dt>Tài khoản</dt><dd>{decoded.account_no}</dd></div><div><dt>Số tiền</dt><dd>{decoded.amount_vnd ? vnd(decoded.amount_vnd) : 'Nhập ở bước tiếp theo'}</dd></div>{decoded.add_info && <div><dt>Nội dung</dt><dd>{decoded.add_info}</dd></div>}</dl><button className="primary-button" onClick={() => review(toTransfer(decoded))}>Kiểm tra chuyển tiền<ArrowUpRight size={17} /></button></div>}</Sheet>
  </div>;
}
