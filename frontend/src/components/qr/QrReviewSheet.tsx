import { ArrowUpRight, QrCode } from 'lucide-react';
import { vnd } from '../../format';
import { Sheet } from '../ui/Sheet';
import { QrSafetyNotice, type DecodedQr } from './QrSafetyNotice';

export function QrReviewSheet({ decoded, onClose, onReview }: {
  decoded: DecodedQr | null;
  onClose: () => void;
  onReview: (decoded: DecodedQr) => void;
}) {
  return <Sheet open={!!decoded} onClose={onClose} title="Thông tin mã QR">{decoded && (
    <div className="qr-decoded" lang="vi">
      <span className="qr-decoded-icon"><QrCode size={29} aria-hidden="true" /></span>
      <h3>{decoded.account_name || 'Người nhận'}</h3>
      <p className="qr-sheet-intro">Kiểm tra thông tin trước khi mở bản nháp chuyển tiền.</p>
      <QrSafetyNotice data={decoded} />
      <dl className="detail-list">
        <div><dt>Ngân hàng</dt><dd>{decoded.bank}</dd></div>
        <div><dt>Tài khoản</dt><dd>{decoded.account_no}</dd></div>
        <div><dt>Số tiền</dt><dd>{decoded.amount_vnd ? vnd(decoded.amount_vnd) : 'Nhập ở bước tiếp theo'}</dd></div>
        {decoded.add_info && <div><dt>Nội dung</dt><dd>{decoded.add_info}</dd></div>}
      </dl>
      <button className="primary-button" onClick={() => onReview(decoded)}>Kiểm tra chuyển tiền<ArrowUpRight size={17} aria-hidden="true" /></button>
    </div>
  )}</Sheet>;
}
