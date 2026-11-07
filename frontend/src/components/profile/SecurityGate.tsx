import { KeyRound, LogOut, ShieldCheck, Wallet } from 'lucide-react';
import type { DemoUser } from '../../types';
import { PinForm } from './TransactionPin';

const STEPS = [
  { icon: <KeyRound size={18} aria-hidden="true" />, text: 'Pick 6 digits only you know. Avoid birthdays and patterns like 123456.' },
  { icon: <Wallet size={18} aria-hidden="true" />, text: 'Transfers, bill payments, savings and card changes ask for this PIN.' },
  { icon: <ShieldCheck size={18} aria-hidden="true" />, text: 'Five wrong tries lock it for 15 minutes. Change it any time in Profile.' },
];

// New accounts land here after their first sign-in and cannot bank until they create a transaction PIN.
export function SecurityGate({ user, done, logout }: { user: DemoUser; done: () => void; logout: () => void }) {
  return <main className="totp-gate" id="main">
    <section className="card totp-gate-card" aria-labelledby="pin-gate-title">
      <span className="totp-gate-icon" aria-hidden="true"><KeyRound size={30} /></span>
      <h1 id="pin-gate-title">Create your transaction PIN</h1>
      <p className="muted">One last step. NovaBank asks for this 6-digit PIN every time money moves, so only you can approve payments.</p>
      <ol className="totp-steps">{STEPS.map((s, i) => <li key={i}>{s.icon}<span>{s.text}</span></li>)}</ol>
      <PinForm user={user} done={done} submitLabel="Create PIN and start banking" />
      <button className="link-button totp-gate-out" onClick={logout}><LogOut size={16} aria-hidden="true" /> Sign out</button>
    </section>
  </main>;
}
