export interface DemoUser { id: string; name: string }
export interface Session { user: DemoUser; csrf_token: string; expires_at: number }
export interface BankAccount { id: string; owner_id: string; owner_name: string; balance_vnd: number; currency: string }
export interface TransferIntent { id: string; source_account_id: string; recipient_account_id: string; recipient_name: string; amount_vnd: number; description: string; status: 'pending' | 'completed' | 'cancelled'; expires_at: number }
export interface BankTransaction { id: string; source_account_id: string; recipient_account_id: string | null; amount_vnd: number; description: string; status: string; created_at: string; intent_id: string | null }
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
  response_source: 'mock' | 'application_template' | 'application_fallback' | 'ollama_tool' | 'ollama_tool_bound';
}
export interface Health { status: string; llm_provider: string; gateway_mode: string; demo_only: boolean }
export interface Decision { decision: 'ALLOW' | 'DENY'; reason_code: string; executed: boolean }
