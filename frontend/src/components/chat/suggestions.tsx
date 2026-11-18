import { Wallet, CreditCard, CircleHelp, Paperclip, QrCode } from 'lucide-react';

export const suggestions = [
  { icon: <Wallet size={20} aria-hidden="true" />, tone: 'balance', chip: 'Balance', title: 'Check balance', detail: 'See what is in your demo account right now.', text: 'Check my account balance' },
  { icon: <CreditCard size={20} aria-hidden="true" />, tone: 'transfer', chip: 'Transaction', title: 'Check a transfer', detail: 'Look up your latest submitted payment.', text: 'What is the status of my latest transfer?' },
  { icon: <QrCode size={20} aria-hidden="true" />, tone: 'qr', chip: 'QR Pay', title: 'Read a QR image', detail: 'Check the payment details before verifying.', text: 'Can I read a QR image in Assistant?' },
  { icon: <CircleHelp size={20} aria-hidden="true" />, tone: 'faq', chip: 'Verification', title: 'Know which code to use', detail: 'Understand Authenticator and transaction PIN.', text: 'When do I use my authenticator or transaction PIN?' },
  { icon: <Paperclip size={20} aria-hidden="true" />, tone: 'support', chip: 'Documents', title: 'Ask about a file', detail: 'Get an answer from a document you upload.', text: 'How do I ask Nova about an uploaded file?' },
];
