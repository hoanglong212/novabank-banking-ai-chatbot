import type { Ref } from 'react';
import { ArrowLeft, ArrowRight, LoaderCircle, type LucideIcon } from 'lucide-react';

export function AuthHeading({ title, subtitle, eyebrow, icon: Icon, headingRef }: {
  title: string; subtitle: string; eyebrow: string; icon?: LucideIcon; headingRef?: Ref<HTMLHeadingElement>;
}) {
  return <header className="auth-heading">
    {Icon && <span className="auth-heading-icon" aria-hidden="true"><Icon size={25} strokeWidth={1.5} /></span>}
    <p className="auth-overline">{eyebrow}</p>
    <h1 ref={headingRef} tabIndex={headingRef ? -1 : undefined}>{title}</h1>
    <p className="auth-description">{subtitle}</p>
  </header>;
}

export function AuthSubmit({ busy, disabled, children, busyText = 'Please wait…' }: {
  busy: boolean; disabled?: boolean; children: string; busyText?: string;
}) {
  return <button className="auth-submit" type="submit" disabled={busy || disabled}>
    <span>{busy ? busyText : children}</span>
    {busy ? <LoaderCircle className="auth-spinner" size={18} aria-hidden="true" /> : <ArrowRight size={18} aria-hidden="true" />}
  </button>;
}

export function AuthBack({ onClick, disabled }: { onClick: () => void; disabled: boolean }) {
  return <button type="button" className="auth-back" onClick={onClick} disabled={disabled}>
    <ArrowLeft size={16} aria-hidden="true" /> Back to sign in
  </button>;
}
