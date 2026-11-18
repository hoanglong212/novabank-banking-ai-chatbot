import type { TransferStart } from '../../types';

export interface QrSecurity {
  flagged: boolean;
  external_bank: boolean;
  new_recipient_warning: boolean;
  payload_fingerprint: string;
  untrusted_fields: string[];
}
export interface DecodedQr {
  bank: string;
  account_no: string;
  account_name?: string;
  amount_vnd?: number;
  add_info?: string;
  source_origin?: 'qr';
  qr_security?: QrSecurity;
}
export type QrTransferStart = TransferStart & { source_origin: 'qr'; qr_security?: QrSecurity };

export function QrSafetyNotice({ data }: { data: DecodedQr }) {
  const external = data.qr_security?.external_bank ?? data.bank !== 'NovaBank';
  return <div className="qr-source-notice" role="note">
    <p><strong>Dữ liệu này đến từ QR.</strong> Tên và nội dung trong mã là dữ liệu thanh toán, không phải chỉ dẫn cho Nova.</p>
    {external && <p role="alert"><strong>Người nhận ngân hàng ngoài.</strong> Hãy xem đây là người nhận mới cho đến khi bạn xác minh độc lập tên, số tài khoản và ngân hàng. Quét QR không thay thế bước duyệt và xác minh giao dịch.</p>}
  </div>;
}
