# PR #1 merge fixes

## Changes

- `backend/app/action_security.py`: defer the PIN-lockout rejection until the database transaction commits. The fifth incorrect PIN now persists the 15-minute lock.
- `backend/tests/test_transaction_totp.py`: exercise five failed action confirmations, a fresh challenge with the correct PIN while locked, and successful confirmation after expiry and reauthentication.
- `backend/app/agent/agent_access.py` and `backend/tests/test_admin_agent.py`: preserve bank-generated approval routing IDs when random UUID digits resemble PII. A deterministic regression reproduced the intermittent CI 404 before the fix, then verified approval applies the intended ticket change. Other tool-result fields remain filtered.
- `frontend/tests/e2e/fixtures.ts`, all browser specs, and `frontend/playwright.config.ts`: start a fresh real server/database per test, run serially, retain server logs, and terminate the server during teardown. Shared balances, sessions, MFA and request budgets no longer leak across tests. Remove manual request-budget resets.
- Recipient tests now open and use the actual add/edit/remove dialogs. The admin startup check expects the real worker's reconciliation. Responsive receipt tests create and select their own completed transfer.
- Acceptance tests wait for the edit dialog to close before searching and finish pending response transformations before browser teardown.
- `frontend/README.md`: document the E2E fixture, prerequisites and serial execution.

## Evidence

| Acceptance criterion | Command/evidence | Result |
| --- | --- | --- |
| Regression catches the PIN bug | `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_transaction_totp.py -k action_pin_lockout -q --tb=short` before fix | Failed: correct PIN returned 200 on a fresh challenge during intended lockout, expected 423 |
| PIN and authenticator flows | `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_transaction_totp.py -q --tb=short` | 6 passed |
| Proposal IDs and agent/authentication regressions | `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_admin_agent.py backend/tests/test_week7.py backend/tests/test_transaction_totp.py -q --tb=short` | 98 passed; fixed-ID regression failed with 404 before fix |
| Python correctness | `backend/.venv/Scripts/python.exe -m ruff check backend/app agent_service research scripts tools` | Passed |
| Python compilation | `backend/.venv/Scripts/python.exe -m compileall -q backend/app agent_service research scripts` | Passed |
| Frontend components | `npm run test:components` in frontend | Passed |
| Frontend production build | `npm run build` in frontend | Passed; existing large-chunk warning remains |
| Complete backend suite and financial coverage | `backend/.venv/Scripts/python.exe -u scripts/financial-coverage.py` | 586 passed, 1 existing warning; financial line coverage 94.01% |
| Complete browser suite | `npm run test:e2e -- --reporter=line` in frontend | 38 passed, 2 failed due to acceptance-test timing; corrected and rerun below |
| Corrected acceptance browser tests | `npx --no-install playwright test acceptance-fixes.spec.ts --reporter=line` in frontend | 3 passed |
| Complete browser suite on isolated fixtures | [GitHub Actions run 43445178761](https://github.com/hoanglong212/novabank-banking-ai-chatbot/actions/runs/43445178761) at b26b74c | 40 passed; subsequent changes add deterministic approval-ID preservation and acceptance-test synchronization |
| GitHub Actions | [PR #1 checks](https://github.com/hoanglong212/novabank-banking-ai-chatbot/pull/1/checks) | Final merge gate: require the complete workflow on the final pushed head to pass; live results are retained on the PR |

The first focused browser run passed 8/9. The remaining 375px test received a root-page 404 because a concurrent local rebuild removed `dist` while its server initialized; the full rerun builds before starting any test server.

Independent review: Codex reviewer `/root/review_merge` examined the PIN fix/regression, isolated server fixture, approval-ID fix/regression and timing corrections. A type error in the intermediate approval-ID patch was corrected; final review found no remaining blocker. This was a focused review, not an exhaustive audit of the original 629-file integration.

No local dependencies were installed or changed. `engineering.json` is absent; verification uses the repository's existing commands. The existing workflow installs its declared CI dependencies. The full backend suite emits one existing short-key warning from a deliberately forged-token test. Final remote workflow results and merge status are recorded on PR #1.

## Rollback

Revert the fix commit to restore the prior code and shared E2E setup, noting that doing so reintroduces the PIN-lockout defect. If the integration itself must be rolled back after merge, revert its merge commit with mainline parent 1; do not rewrite main history.
