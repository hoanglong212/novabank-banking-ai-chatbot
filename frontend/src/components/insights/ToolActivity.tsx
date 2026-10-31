import { CheckCheck, ShieldAlert, ShieldCheck } from 'lucide-react';

import type { ToolEvent } from '../../types';

interface ToolActivityProps {
  events: ToolEvent[];
}

const ACTIONS: Record<string, string> = {
  get_account_balance: 'Balance check',
  get_recent_transactions: 'Transaction history',
  get_transaction_status: 'Transaction lookup',
  search_banking_faq: 'Help article search',
  create_support_ticket: 'Support ticket',
  create_vietqr: 'VietQR code',
  create_transfer: 'Transfer draft (needs your OTP)',
  input_guard: 'Message screening',
};

const REASONS: Record<string, string> = {
  ACCOUNT_NOT_OWNED: 'Not your account',
  TRANSACTION_NOT_OWNED: 'Not your transaction',
  PROMPT_INJECTION: 'Tried to override safety rules',
  SECRET_REDACTED: 'Sensitive data removed',
  NOT_REQUESTED_BY_USER: 'You did not ask for this',
  INVALID_ARGUMENTS: 'Incomplete request',
  UNKNOWN_TOOL: 'Unsupported action',
};

// Plain-language audit trail of what the assistant tried and whether policy allowed it.
export function ToolActivity({
  events,
}: ToolActivityProps) {
  return (
    <div className="activity-list">
      {events.length === 0 ? <div className="empty-activity">
        <ShieldCheck size={22} aria-hidden="true" />
        <p>No actions yet</p>
        <small>Every action Nova takes in this chat is checked and listed here.</small>
      </div> : events.slice(-6).reverse().map(e => <div className="event" key={e.id}>
        <div className="event-content">
          <strong title={e.tool_name}>
            {ACTIONS[e.tool_name] ?? e.tool_name}
          </strong>
          <span>
            {e.decision === 'ALLOW' ? 'Allowed by policy' : REASONS[e.reason_code] ?? e.reason_code.toLowerCase().replace(/_/g, ' ')}
          </span>
        </div>
        <span className={`event-label ${e.decision === 'ALLOW' ? 'allowed' : 'denied'}`}>
          {e.decision === 'ALLOW' ? <CheckCheck size={13} aria-hidden="true" /> : <ShieldAlert size={13} aria-hidden="true" />}
          {e.decision === 'ALLOW' ? 'Allowed' : 'Blocked'}
        </span>
      </div>)}
    </div>
  );
}
