import { ArrowRight, CheckCheck, ShieldAlert } from 'lucide-react';

import type { DemoUser, Decision } from '../../types';

interface PolicyTestProps {
  user: DemoUser | null;
  busy: boolean;
  toolName: string;
  setToolName: (tool: string) => void;
  accountId: string;
  setAccountId: (id: string) => void;
  policyResult: Decision | null;
  setPolicyResult: (result: Decision | null) => void;
  runPolicyDryRun: () => void;
}

export function PolicyTest({
  user,
  busy,
  toolName,
  setToolName,
  accountId,
  setAccountId,
  policyResult,
  setPolicyResult,
  runPolicyDryRun,
}: PolicyTestProps) {
  return (
    <div className="policy-test">
      <p>Checks permissions without executing the tool.</p>
      <label>Tool<select value={toolName} onChange={e => {
        setToolName(e.target.value);
        setPolicyResult(null);
      }}>
        <option value="get_account_balance">Check balance</option>
        <option value="get_transaction_status">Track a transaction</option>
        <option value="search_banking_faq">Search FAQs</option>
      </select>
      </label>
      {toolName === 'get_account_balance' && <label>Account ID<input
        value={accountId}
        onChange={e => {
          setAccountId(e.target.value);
          setPolicyResult(null);
        }}
        placeholder="ACC-ALICE-001" />
      </label>}
      {toolName === 'get_transaction_status' && <div className="test-note">Demo transaction TX-2001 belongs to Bob.</div>}
      <button className="test-button" onClick={runPolicyDryRun} disabled={!user || busy}>Check permissions <ArrowRight size={16} aria-hidden="true" />
      </button>
      {policyResult && <div role="status" className={`policy-result ${policyResult.decision.toLowerCase()}`}>
        {policyResult.decision === 'ALLOW' ? <CheckCheck size={17} aria-hidden="true" /> : <ShieldAlert size={17} aria-hidden="true" />}
        <span>
          <strong>
            {policyResult.decision === 'ALLOW' ? 'Permission granted' : 'Permission denied'}
          </strong>
          <small>
            {policyResult.reason_code.toLowerCase().replace(/_/g, ' ')}
          </small>
        </span>
      </div>}
    </div>
  );
}
