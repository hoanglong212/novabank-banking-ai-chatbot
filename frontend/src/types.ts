// The signed-in customer; token is the short-lived JWT from /api/auth/login.
export type UserRole = 'customer' | 'support' | 'operations' | 'auditor' | 'admin';
export interface DemoUser { id: string; name: string; token: string; sessionId?: string; role?: UserRole; permissions?: string[] }
export interface Conversation { id: string; owner_id: string; title: string; created_at: string; updated_at: string }
export interface ChatMessage { id: string; conversation_id: string; role: 'user' | 'assistant'; content: string; created_at: string }
export interface ToolEvent {
  id: string;
  tool_name: string;
  decision: 'ALLOW' | 'DENY';
  reason_code: string;
  executed: number;
  arguments: Record<string, unknown>;
  created_at: string;
}
export interface SendResponse {
  message: ChatMessage;
  tool_events: ToolEvent[];
  response_source: 'mock' | 'application_template' | 'application_fallback' | 'ollama_tool' | 'ollama_tool_bound' | 'langgraph' | 'input_guard' | 'agent_service';
}
export interface Health { status: string; llm_provider: string; gateway_mode: string; demo_only: boolean; agent_mode?: string }
export interface Decision { decision: 'ALLOW' | 'DENY'; reason_code: string; executed: boolean }
export interface MfaChallenge { mfa_required: true; challenge_id: string; method: 'email' | 'totp'; expires_in: number; message: string }
export interface LoginResponse {
  access_token: string; refresh_token: string; session_id: string; expires_in: number;
  idle_expires_at: number; absolute_expires_at: number; device_token?: string;
  user:{ id: string; name: string; role: UserRole; permissions: string[] };
}
export interface UserSession {
  id: string; created_at: number; last_active_at: number; absolute_expires_at: number;
  ip: string; user_agent: string; method: string; current: boolean;
}
export interface LoginAttempt { id: string; created_at: number; ip: string; user_agent: string; result: string; method: string }
export interface MfaStatus { totp_enabled: boolean; email_fallback: boolean; pin_set?: boolean; setup_required?: boolean }
export interface TotpSetup { secret: string; otpauth_uri: string; qr_png?: string; expires_in: number }
export interface Transaction {
  id: string; amount_vnd: number; status: string; description: string; direction: 'in' | 'out'; date: string;
  account_id?: string; owner_id?: string; holder_name?: string; created_at?: string; transfer_id?: string | null;
  balance_after_vnd?: number | null; counterparty_name?: string | null; counterparty_account?: string | null;
  counterparty_bank?: string | null; fee_vnd?: number | null;
}
export interface Page<T> { items: T[]; total: number; limit: number; offset: number }
export interface TransactionFilters {
  q?: string; direction?: string; status?: string; from_date?: string; to_date?: string; account_id?: string;
  limit?: number; offset?: number;
}
export interface BankNotification {
  id: string; transaction_id: string | null; resource_id?: string | null; kind: string; title: string; body: string;
  created_at: string; read_at: string | null; category?: NotificationCategory;
}
export type NotificationCategory = 'transactions' | 'account';
export interface NotificationPage extends Page<BankNotification> { unread_count: number; unread_by_category?: Record<NotificationCategory, number> }
export interface Announcement {
  id: string; kind: 'CAMPAIGN' | 'NOTICE'; title: string; tag: string; body: string;
  action_label: string | null; action_path: string | null; published_at: string; ends_at: string | null;
}
export interface AuditEvent {
  id: string; owner_id: string; action: string; resource_id: string; reason_code: string;
  before_balance_vnd: number | null; after_balance_vnd: number | null; created_at: string;
}
export interface Profile {
  id: string; name: string;
  accounts: { id: string; holder_name: string; balance_vnd: number; currency: string }[];
  transactions: Transaction[];
}
export interface Bank { bin: string; code: string; shortName: string; name: string; logo: string }
export interface VietQR { bank: string; bin: string; account_no: string; account_name: string; amount_vnd: number | null; add_info: string; image: string; payload: string }
// Codes are delivered to the simulated mailbox, never returned with a draft.
export interface Transfer {
  id: string; from_account: string; to_bank: string; to_account: string; to_name: string; amount_vnd: number;
  content: string; status: 'PENDING_OTP' | 'PENDING' | 'COMPLETED' | 'FAILED'; otp_expires_at?: string; transaction_id?: string | null; fee_vnd?: number;
  balance_vnd?: number; expires_at?: string; otp_method?: 'totp' | 'pin' | 'email';
}
export interface TransferStart { draftId?: string; to_bank?: string; to_account?: string; to_name?: string; amount_vnd?: number; content?: string }
