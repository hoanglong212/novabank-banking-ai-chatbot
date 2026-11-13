import type { ReactNode } from 'react';
import { ArrowUpRight, CheckCircle2, Inbox, ShieldCheck } from 'lucide-react';
import { Sheet } from '../ui/Sheet';

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return <div className="service-empty"><Inbox size={28} strokeWidth={1.4} /><h3>{title}</h3><p>{children}</p></div>;
}
export function ServiceHeading({ eyebrow, title, children, action }: { eyebrow?: string; title: string; children?: ReactNode; action?: ReactNode }) {
  return <div className="service-heading"><div>{eyebrow && <p className="service-eyebrow">{eyebrow}</p>}<h2>{title}</h2>{children && <p>{children}</p>}</div>{action}</div>;
}
export function Metric({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return <div className="service-metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>;
}
export function ServiceNote({ children }: { children: ReactNode }) {
  return <p className="service-note"><ShieldCheck size={16} aria-hidden="true" /><span>{children}</span></p>;
}
export function ResultNote({ children }: { children: ReactNode }) {
  return <div role="status" className="success-note"><CheckCircle2 size={18} /><span>{children}</span></div>;
}
export function ConfirmRemove({ title, open, close, busy, action, children }: { title: string; open: boolean; close: () => void; busy: boolean; action: () => void; children: ReactNode }) {
  return <Sheet open={open} title={title} onClose={close}><div className="service-dialog"><div>{children}</div><div className="service-actions"><button className="secondary-button" disabled={busy} onClick={close}>Keep it</button><button className="primary-button" disabled={busy} onClick={action}>{busy ? 'Removing…' : 'Remove'}<ArrowUpRight size={16} /></button></div></div></Sheet>;
}
export const today = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' });
export const displayDate = (value: string) => new Date(value.length === 10 ? value + 'T12:00:00' : value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
