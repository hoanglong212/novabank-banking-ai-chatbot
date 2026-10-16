# Reliability fixes — 16 October 2026

Implementation and local verification are complete. Independent review is pending; this is not a claim of full framework sign-off. Baseline: 10/15 application scenarios passed. After fixes: 15/15 passed using the live local Ollama model (`llama3.2:3b`) and browser UI.

## Acceptance criteria and evidence

| Case | Result | Observed behavior |
|---|---|---|
| T01 | PASS | Greeting and capabilities; no raw JSON |
| T02 | PASS | Curated VietQR answer, FAQ ALLOW/executed |
| T03 | PASS | Locked-card guidance, no personal-data request |
| T04 | PASS | No invented transfer fee |
| T05 | PASS | Alice balance 12,500,000 VND |
| T06 | PASS | TX-1002, PENDING, 950,000 VND |
| T07 | PASS | Actual local ticket ID and OPEN; no personal-data request |
| T08 | PASS | Correct balance and 3,000,000 VND comparison; explicitly no transfer |
| T09 | PASS | Follow-up resolves user-supplied TX-1002 |
| T10 | PASS | Foreign account denied, executed=0 |
| T11 | PASS | Foreign transaction denied, executed=0 |
| T12 | PASS | API/UI dry runs show ALLOW/DENY, always executed=0 |
| T13 | PASS | Ten messages retain exact order/content after refresh |
| T14 | PASS | Switching conversations restores exact content |
| T15 | PASS | Alice → Bob → Alice restores each user's list without 404 |

Evidence: [live API](postfix-test-evidence-2026-10-16.json), [repeats](postfix-test-repeat-evidence-2026-10-16.json), [browser](postfix-test-ui-evidence-2026-10-16.json), [final ticket-consent recheck](postfix-consent-evidence-2026-10-16.json). Baseline reports/evidence remain unchanged. Validation conversations remain available for inspection.

T01, T05, T06, T07, T08, T09, T10 and T11 each passed three runs. Across 33 message responses in the initial API run plus two repeat rounds: 15 `ollama_tool`, 15 `ollama_tool_bound`, 3 `application_template`, 0 `application_fallback`. Fallback paths were tested with controlled malformed/missing native calls in pytest. After the final consent-parser tightening, T07 and three non-consenting prompts were rerun live: exactly one ticket for T07, none for the other prompts.

These are application outcomes. The application chooses the operation and supplies only that tool schema to Ollama. It renders all final replies from authoritative results. Therefore even `ollama_tool` is not evidence of unconstrained model tool selection or reasoning accuracy.

## Changes

- `backend/app/banking_workflow.py`: user-originated resource/context binding, explicit ticket intent, supported amount comparison, curated replies.
- `backend/app/agent.py`: native-call shape validation, one operation per turn, no raw model-text execution, observable fallback, unavailable Ollama remains 503.
- `backend/app/tools.py`: audit rejected model proposals without retaining their arguments.
- `backend/app/main.py`, `frontend/src/types.ts`: expose response provenance.
- `frontend/src/App.tsx`: separate cancellation for list/message requests, identity-scoped selection, clearing draft/results on user changes, mutation busy guards.
- `backend/tests/test_reliability.py`, `backend/tests/test_agent.py`: regression coverage and updated guarded-agent contract.
- `frontend/scripts/browser-session.mjs`, `frontend/scripts/check-user-switch.mjs`, `frontend/package.json`: reproducible identity-switch regression using existing Node/Edge.
- README and implementation plan updated. No dependencies or services installed for these fixes.

## Checks actually run

| Command | Working directory | Result |
|---|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q --tb=short` | backend | 49 passed; one existing Starlette/httpx deprecation warning |
| `npm.cmd run build --prefix frontend` | project root | PASS; existing Tailwind no-utility-classes warning |
| `npm.cmd run test:identity --prefix frontend` | project root | PASS: three identity-switch rounds plus rapid switches with network latency |
| `backend/.venv/Scripts/python.exe .local/validate-banking.py` | project root | Live API evidence recorded |
| `backend/.venv/Scripts/python.exe .local/repeat-validation.py` | project root | Two additional rounds recorded |
| `node .local/validate-ui.mjs` | project root | T12–T15 and tool activity verified |
| `backend/.venv/Scripts/python.exe .local/validate-consent.py` | project root | Final consent scenarios passed |

Before implementation, the new reliability scenarios failed and the browser identity check reproduced `Conversation not found`. Additional consent tests also failed before the parser tightening, then passed. No new application logic was changed after the final passing checks (only documentation/module description).

## Review, limitations and rollback

Self-review covered ownership, invented IDs, malformed proposals, duplicate ticket creation, ticket consent and stale frontend requests. No independent reviewer was dispatched under the local framework adaptation; independent review remains pending. The optional framework CLI check could not run because `engineering.json` is absent (ENOENT). No separate lint or general end-to-end gate is claimed.

Intent recognition is constrained and keyword-based. Supported amount formats are limited; unclear amounts request clarification. This is not a general multilingual intent or PII detector, and no 20-variant model benchmark was performed. User-provided ticket text is stored as submitted. Demo authentication/local policy and the unchanged offline mock mode retain their documented limitations. Provenance is returned by message POST, not stored on historical messages. Browser verification used Edge; other browsers were not tested.

There is no Git repository. Pre-change backups of `agent.py`, `tools.py`, `main.py`, and `App.tsx` are in `.local/before-reliability/`. To roll back behavior, stop the local app, restore those four files to their original locations, remove the new workflow import/file and corresponding regression tests or restore the old agent test expectations, then rebuild the frontend and restart the backend. The additive API type and browser script can remain or be removed manually. No database schema migration was made; rollback does not require deleting histories or tickets.
