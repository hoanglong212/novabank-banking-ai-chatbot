import { Wallet, CreditCard, CircleHelp, ClipboardList } from 'lucide-react';

export const suggestions = [
  { icon: <Wallet size={22} aria-hidden="true" />, tone: 'balance', chip: 'Balance', title: 'Check balance', detail: 'See what is in your demo account right now.', text: 'Check my account balance' },
  { icon: <CreditCard size={22} aria-hidden="true" />, tone: 'transfer', chip: 'Transaction', title: 'Track a transaction', detail: 'Follow a payment from sent to settled.', text: 'Check transaction TX-1002' },
  { icon: <CircleHelp size={22} aria-hidden="true" />, tone: 'faq', chip: 'Questions', title: 'Banking questions', detail: 'VietQR, transfers and everyday services.', text: 'What is VietQR and what should I check before scanning a code?' },
  { icon: <ClipboardList size={22} aria-hidden="true" />, tone: 'support', chip: 'Support', title: 'Get support', detail: 'Open a ticket and we will follow up.', text: 'Create a support ticket for my pending transaction' },
];
