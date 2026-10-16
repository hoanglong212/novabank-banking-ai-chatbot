import { X, Wrench, Shield, CircleHelp } from 'lucide-react';

import type { Health, ToolEvent } from '../../types';

import type { ComponentProps } from 'react';
import { PolicyTest } from './PolicyTest';
import { ToolActivity } from './ToolActivity';

interface TestingInsightsProps {
  health: Health | null;
  events: ToolEvent[];
  setPolicyPanelOpen: (open: boolean) => void;
  policy: ComponentProps<typeof PolicyTest>;
}

export function TestingInsights({
  health,
  events,
  setPolicyPanelOpen,
  policy,
}: TestingInsightsProps) {
  return (
    <>
      <button
        className="inspector-overlay"
        aria-label="Close testing insights"
        onClick={() => setPolicyPanelOpen(false)} />
      <aside className="inspector" id="policy-panel" aria-label="Testing insights">
        <div className="inspector-header">
          <strong>Testing insights</strong>
          <button
            className="icon-button"
            aria-label="Close testing insights"
            onClick={() => setPolicyPanelOpen(false)}>
            <X size={19} />
          </button>
        </div>
        <div className="inspector-content">
          <div className="inspector-card">
            <div className="card-kicker">Access control</div>
            <h3>Demo policy layer</h3>
            <p>Permissions are checked before tools run. The team's live gateway is not connected yet.</p>
            <dl className="stats-row">
              <div>
                <dt>Gateway</dt>
                <dd>
                  {health?.gateway_mode ?? '—'}
                </dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>
                  {health?.llm_provider ?? '—'}
                </dd>
              </div>
            </dl>
          </div>
          <div className="panel-section-heading">
            <Wrench size={16} aria-hidden="true" /> Tool activity <span>
              {events.length}
            </span>
          </div>
          <ToolActivity events={events} />
          <div className="panel-section-heading">
            <Shield size={16} aria-hidden="true" /> Check permissions <span className="dryrun-label">Dry run</span>
          </div>
          <PolicyTest {...policy} />
          <div className="inspector-info">
            <CircleHelp size={16} aria-hidden="true" />
            <p>Architecture demonstration only. This is not a banking security certification.</p>
          </div>
        </div>
      </aside>
    </>
  );
}
