# Balance consistency — 2026-11-15

Generic balance requests now use the sum of the signed-in customer's payment accounts, the same scope as Home's `/api/me` total. Explicit account requests retain ownership checks and identify the requested account. The bank renders balance answers from the latest allowed balance tool result in that run, both for streaming previews and saved messages. Without a successful read, it reports that the balance has not been verified. Lab gateway-off behavior is unchanged.

## Acceptance evidence

- `backend/tests/test_balance_consistency.py`: dashboard total, multiple accounts, explicit account, invented numeric and written-out balances, preview and final output.
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_balance_consistency.py backend/tests/test_AI_12.py backend/tests/test_agent_boundary.py backend/tests/test_agent_false_completion.py -q --tb=short`: **16 passed**.
- `cd frontend; npm.cmd run test:components`: **19 groups passed**.
- `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short`: **683 passed, 1 xfailed**, 242.47 seconds. One warning comes from the existing short-key token-payload test. This run started before the final tightening of the no-tool fallback; the final affected paths were rechecked in the 16-test run above.
- Local `/` returned HTTP 200 and `/api/ready` returned `ready` with `qwen2.5:7b` after the final restart. `git diff --check` passed.

## Files and operation

Changed `backend/app/agent/agent_access.py`, `backend/app/agent_output.py`, `backend/tests/test_AI_12.py`; added `backend/tests/test_balance_consistency.py`. Local services were restarted with the existing `.local/local-deploy/start.ps1`, using the existing local database and Ollama at port 11435.

## Limits and rollback

This is a targeted correction for the reported balance discrepancy, not a complete manual audit of every feature. Browser E2E and real-model conversational acceptance have not been run for this change. Existing saved answers retain their original text; ask a new balance question. Dashboard data is refreshed on navigation, so concurrent changes from another session can still require reopening Home. Independent review is pending; only implementer review was performed. No engineering.json was found. No frontend build was required because frontend source was unchanged.

To roll back, reverse only this change in the listed files and restart the existing local launcher. No database migration is involved.
