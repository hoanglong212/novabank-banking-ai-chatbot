export interface TransferSummary {
  id: string; owner_id: string; from_account: string; to_bank: string; to_account: string; to_name: string;
  internal: number; amount_vnd: number; content: string; transaction_id: string | null; recorded_at: string;
  status: 'COMPLETED' | 'PENDING' | 'FAILED'; failure_reason: string | null;
}
export interface TransferDay { date: string; internal_vnd: number; external_vnd: number; completed: number }
export interface TransferMetrics { attempts: number; completed: number; failed: number; pending: number; volume_vnd: number; internal_vnd: number; external_vnd: number; success_rate: number | null }
export interface Reconciliation {
  id: string; created_at: string; balanced: boolean; ledger_total_vnd: number;
  mismatches: { account_id: string; balance_vnd: number; ledger_balance_vnd: number }[];
  unbalanced_journals: { journal_id: string; total_vnd: number; entry_count: number }[];
}
export interface DashboardResponse {
  reconciliation: Reconciliation | null;
  dashboard: {
    updated_at: string; period: { days: number; from_date: string; to_date: string; timezone: string };
    metrics: TransferMetrics; previous: TransferMetrics; daily: TransferDay[];
    snapshot: { customers: number; active_customers: number; unverified_customers: number; accounts: number; payment_balance_vnd: number; frozen_accounts: number; open_tickets: number; pending_settlements: number };
    recent: TransferSummary[]; queues: { pending: TransferSummary[]; failed: TransferSummary[] };
    events: { id: string; owner_id: string; action: string; resource_id: string; created_at: string }[];
  };
}
export const shortDay = (value: string) => new Date(value + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
export const bankTime = (value: string) => new Date(value).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' });
export const count = (value: number) => value.toLocaleString('en-US');
