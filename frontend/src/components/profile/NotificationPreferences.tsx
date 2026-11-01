import type { DemoUser } from '../../types';
import { Feedback, Loading, send, useOperation, useResource } from '../explore/shared';

export function NotificationPreferences({ user }: { user: DemoUser }) {
  const state = useResource<{ bill_reminders: boolean; budget_alerts: boolean }>(user, '/customer/notification-preferences');
  const op = useOperation();
  return <section className="card service-section"><h2 className="card-title">Notification preferences</h2><p className="muted">Choose optional in-app reminders. Security and money alerts stay on.</p><Loading state={state} /><Feedback state={op} />{state.data && <form key={JSON.stringify(state.data)} className="service-form" onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void op.run(async () => { await send(user, '/customer/notification-preferences', { bill_reminders: data.get('bills') === 'on', budget_alerts: data.get('budgets') === 'on' }, 'PUT'); state.reload(); op.setMessage('Notification preferences saved.'); }); }}><label className="check-field"><input type="checkbox" name="bills" defaultChecked={state.data.bill_reminders} />Saved bill reminders</label><label className="check-field"><input type="checkbox" name="budgets" defaultChecked={state.data.budget_alerts} />Monthly budget alerts</label><button className="secondary-button" disabled={op.busy}>Save notification preferences</button></form>}</section>;
}
