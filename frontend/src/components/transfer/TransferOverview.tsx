import { ArrowDown, Landmark, Wallet } from 'lucide-react';
import { vnd } from '../../format';
import './transfer-review.css';

interface TransferOverviewProps {
  amount: number;
  from?: string;
  to: string;
  bank: string;
  recipient?: string;
  fee?: number;
  memo?: string;
}

export function TransferOverview({ amount, from, to, bank, recipient, fee, memo }: TransferOverviewProps) {
  return <section className="transfer-overview" aria-label="Payment details">
    <div className="transfer-overview-total">
      <span>Transfer amount</span>
      <strong>{vnd(amount)}</strong>
    </div>
    <div className="transfer-overview-route">
      <div><span className="transfer-overview-icon"><Wallet size={18} aria-hidden="true" /></span>
        <p><span>From</span><strong>{from || 'Your primary payment account'}</strong></p>
      </div>
      <ArrowDown className="transfer-overview-arrow" size={15} aria-hidden="true" />
      <div><span className="transfer-overview-icon"><Landmark size={18} aria-hidden="true" /></span>
        <p><span>To</span><strong>{recipient || bank}</strong><small>{to}</small>
          {recipient && <small>{bank}</small>}
          {recipient === '' && <small>Recipient name unavailable</small>}
        </p>
      </div>
    </div>
    {(fee !== undefined || memo) && <dl className="detail-list transfer-overview-details">
      {memo && <div><dt>Note</dt><dd>{memo}</dd></div>}
      {fee !== undefined && <>
        <div><dt>Fee</dt><dd>{fee ? vnd(fee) : 'Free'}</dd></div>
        <div><dt>Total debit</dt><dd>{vnd(amount + fee)}</dd></div>
      </>}
    </dl>}
  </section>;
}
