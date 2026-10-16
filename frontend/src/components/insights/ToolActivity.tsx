import { Database, CheckCheck, ShieldAlert } from 'lucide-react';

import type { ToolEvent } from '../../types';

interface ToolActivityProps {
  events: ToolEvent[];
}

export function ToolActivity({
  events,
}: ToolActivityProps) {
  return (
    <div className="activity-list">
      {events.length === 0 ? <div className="empty-activity">
        <Database size={22} aria-hidden="true" />
        <p>No activity yet</p>
        <small>Tool checks will appear here.</small>
      </div> : events.slice(-6).reverse().map(e => <div className="event" key={e.id}>
        <div className="event-content">
          <strong title={e.tool_name}>
            {e.tool_name}
          </strong>
          <span>
            {e.reason_code.replace(/_/g, ' ')}
          </span>
        </div>
        <span className={`event-label ${e.decision === 'ALLOW' ? 'allowed' : 'denied'}`}>
          {e.decision === 'ALLOW' ? <CheckCheck size={13} aria-hidden="true" /> : <ShieldAlert size={13} aria-hidden="true" />}
          {e.decision}
        </span>
      </div>)}
    </div>
  );
}
