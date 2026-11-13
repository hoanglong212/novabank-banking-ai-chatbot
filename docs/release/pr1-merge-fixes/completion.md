# PR #1 merge fixes

## Changes

- `backend/app/action_security.py`: defer the PIN-lockout rejection until the database transaction commits. The fifth incorrect PIN now persists the 15-minute lock.
- `backend/tests/test_transaction_totp.py`: exercise five failed action confirmations, a fresh challenge with the correct PIN while locked, and successful confirmation after expiry and reauthentication.
- `frontend/tests/e2e/fixtures.ts`, all browser specs, and `frontend/playwright.config.ts`: start a fresh real server/database per test, run serially, retain server logs, and terminate the server during teardown. Shared balances, sessions, MFA and request budgets no longer leak across tests. Remove manual request-budget resets.
- Recipient tests now open and use the actual add/edit/remove dialogs. The admin startup check expects the real worker's reconciliation. Responsive receipt tests create and select their own completed transfer.
- `frontend/README.md`: document the E2E fixture, prerequisites and serial execution.

## Evidence

| Acceptance criterion | Command/evidence | Result |
| --- | --- | --- |
| Regression catches the PIN bug | `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_transaction_totp.py -k action_pin_lockout -q --tb=short` before fix | Failed: correct PIN returned 200 on a fresh challenge during intended lockout, expected 423 |
| PIN and authenticator flows | `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_transaction_totp.py -q --tb=short` | 6 passed |
| Python correctness | `backend/.venv/Scripts/python.exe -m ruff check backend/app agent_service research scripts tools` | Passed |
| Python compilation | `backend/.venv/Scripts/python.exe -m compileall -q backend/app agent_service research scripts` | Passed |
| Frontend components | `npm run test:components` in frontend | Passed |
| Frontend production build | `npm run build` in frontend | Passed; existing large-chunk warning remains |
| Complete backend suite and financial coverage | `backend/.venv/Scripts/python.exe scripts/financial-coverage.py` | Pending |
| Complete browser suite | `npm run test:e2e -- --reporter=line` in frontend | Pending |
| GitHub Actions | PR #1 checks on final code | Pending |

The first focused browser run passed 8/9. The remaining 375px test received a root-page 404 because a concurrent local rebuild removed `dist` while its server initialized; the full rerun builds before starting any test server.

Independent review: Codex reviewer `/root/review_merge` examined the PIN fix/regression and isolated server fixture and found no blocking issues. This was a focused review, not an exhaustive audit of the original 629-file integration.

No dependencies were installed or changed. `engineering.json` is absent; verification uses the repository's existing commands. Full validation and merge are pending until the rows above are updated.

## Rollback

Revert the fix commit to restore the prior code and shared E2E setup, noting that doing so reintroduces the PIN-lockout defect. If the integration itself must be rolled back after merge, revert its merge commit with mainline parent 1; do not rewrite main history.
