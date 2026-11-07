import { useState } from 'react';
import type { DemoUser } from '../../types';
import { send, useOperation, useResource, type ActionDraft, type ActionResult } from './shared';

export interface PaymentAccount { id: string; nickname: string; balance_vnd: number; status: string }
export function useProducts<T>(user: DemoUser, kind: 'cards' | 'bills' | 'savings') {
  const state = useResource<{ items: T[]; rates_bps?: Record<string, number> }>(user, '/products/' + kind);
  const accounts = useResource<{ items: PaymentAccount[] }>(user, '/customer/accounts');
  const op = useOperation();
  const [draft, setDraft] = useState<ActionDraft | null>(null);
  const prepare = (body: Record<string, unknown>) => void op.run(async () => setDraft(await send<ActionDraft>(user, '/products/actions', body)));
  function complete(result: ActionResult) {
    const messages: Record<string, string> = { FREEZE_CARD: 'Card frozen. New purchases are paused.', UNFREEZE_CARD: 'Card unfrozen. You can make purchases again.', CARD_PURCHASE: 'Purchase completed. Your card history has been updated.', REPAY_CARD: 'Repayment completed. Your credit balance has been updated.', PAY_BILL: 'Bill paid. Your balance and activity have been updated.', OPEN_SAVINGS: 'Savings deposit opened. Your money is set aside.', WITHDRAW_SAVINGS: 'Savings withdrawn to your original payment account.' };
    setDraft(null); op.setMessage(messages[result.kind ?? ''] ?? result.message); state.reload(); accounts.reload();
  }
  return { state, accounts, op, draft, setDraft, prepare, complete };
}
