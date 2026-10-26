import { Wallet, CreditCard, CircleHelp, ClipboardList, QrCode } from 'lucide-react';

export const suggestions = [
  { icon: <Wallet size={20} aria-hidden="true" />, tone: 'balance', chip: 'Balance', title: 'Check balance', detail: 'See what is in your demo account right now.', text: 'Check my account balance' },
  { icon: <CreditCard size={20} aria-hidden="true" />, tone: 'transfer', chip: 'Transaction', title: 'Track a transaction', detail: 'Follow a payment from sent to settled.', text: 'Check transaction TX-1002' },
  { icon: <QrCode size={20} aria-hidden="true" />, tone: 'qr', chip: 'VietQR', title: 'Create a VietQR code', detail: 'Generate a payment QR through the VietQR API.', text: 'Create a VietQR for Vietcombank account 0123456789, 50k, content coffee' },
  { icon: <CircleHelp size={20} aria-hidden="true" />, tone: 'faq', chip: 'Questions', title: 'Banking questions', detail: 'VietQR, transfers and everyday services.', text: 'What is VietQR and what should I check before scanning a code?' },
  { icon: <ClipboardList size={20} aria-hidden="true" />, tone: 'support', chip: 'Support', title: 'Get support', detail: 'Open a ticket and we will follow up.', text: 'Create a support ticket for my pending transaction' },
];
