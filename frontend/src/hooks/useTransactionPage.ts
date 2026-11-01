import { useEffect, useState } from 'react';
import { api } from '../api';
import type { DemoUser, Page, Transaction, TransactionFilters } from '../types';

export function useTransactionPage(user: DemoUser, admin = false, initial: Transaction[] = []) {
  const [filters, setFilters] = useState<TransactionFilters>({ limit: 20, offset: 0 });
  const [data, setData] = useState<Page<Transaction>>({ items: initial, total: initial.length, limit: 20, offset: 0 });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError(null);
    (admin ? api.adminTransactions(user, filters) : api.transactions(user, filters))
      .then(result => { if (active) setData(result); })
      .catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [user, admin, filters, attempt]);
  return { data, busy, error, retry: () => setAttempt(n => n + 1),
    apply: (next: TransactionFilters) => setFilters(previous => ({ ...previous, ...next, offset: 0 })),
    move: (offset: number) => setFilters(previous => ({ ...previous, offset })),
  };
}
