// The signed-in customer; token is the short-lived JWT from /api/auth/login.
export interface DemoUser { id: string; name: string; token: string }
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
  response_source: 'mock' | 'application_template' | 'application_fallback' | 'ollama_tool' | 'ollama_tool_bound' | 'langgraph' | 'input_guard';
}
export interface Health { status: string; llm_provider: string; gateway_mode: string; demo_only: boolean }
export interface Decision { decision: 'ALLOW' | 'DENY'; reason_code: string; executed: boolean }
export interface LoginResponse { access_token: string; expires_in: number; user: { id: string; name: string } }
export interface Transaction {
  id: string; amount_vnd: number; status: string; description: string; direction: 'in' | 'out'; date: string;
}
export interface Profile {
  id: string; name: string;
  accounts: { id: string; holder_name: string; balance_vnd: number; currency: string }[];
  transactions: Transaction[];
}
export interface Bank { bin: string; code: string; shortName: string; name: string; logo: string }
export interface VietQR { bank: string; bin: string; account_no: string; account_name: string; amount_vnd: number | null; add_info: string; image: string }
// A draft is PENDING_OTP until the customer confirms; demo_otp stands in for the bank's SMS.
export interface Transfer {
  id: string; from_account: string; to_bank: string; to_account: string; to_name: string; amount_vnd: number;
  content: string; status: 'PENDING_OTP' | 'COMPLETED' | 'FAILED'; otp_expires_at?: string; transaction_id?: string | null;
  demo_otp?: string; balance_vnd?: number;
}
export interface TransferStart { draftId?: string; to_bank?: string; to_account?: string; to_name?: string; amount_vnd?: number; content?: string }
