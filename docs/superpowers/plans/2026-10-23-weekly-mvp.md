# NovaBank weekly MVP implementation plan

Execution: sequential, using msi-aef-executing-plans. User approved the design in conversation and requested implementation, stopping on errors or consequential questions. No additional design approval required.

Goal: authenticated banking demo, read-only LangGraph chat with Presidio, QR and atomic simulated transfers.

Architecture: preserve React/FastAPI/SQLite/Ollama. Cookie JWT plus revocable server sessions. Keep transfer writes outside chat. Use one-origin UI/API and HTTPS for camera.

Spec: approved conversation, including cookie/CSRF, request-local PII mappings, read-only tools, intent-based idempotency and day-3 vertical slice.

## Constraints and review focus
- Preserve existing user evidence and demo database; evaluation uses temporary databases and synthetic PII only.
- Report native model proposals separately from application-bound/fallback outcomes.
- No plaintext secrets in persisted conversation/log/checkpoint; data ownership checked server-side.
- Repeated intent confirmation must not debit twice; concurrent debits must not overspend.
- Session reload, expiration, CSRF and cross-user conversation isolation require tests.
- Stop and report actual evaluation defects before extending implementation, per user instruction.

## Tasks
- [ ] 1. Baseline: scripts/benchmark_day1.py and scripts/evaluate_pii.py; output reproducible JSON evidence in docs/day1-evaluation-2026-10-23/. Run 20 native and 20 guarded model cases, with explicit expected tools, arguments and business reply checks. Trial Presidio pattern recognizers/anonymizer on held-out synthetic structured PII; report misses, false positives and workflow changes. Record dependency versions and limitations.
- [ ] 2. Auth: backend/app/auth.py, database.py, main.py; frontend/src/api.ts and login UI. Tests: forged/expired/revoked JWT, CSRF, reload, rate limit, owner isolation. Cookie JWT, absolute expiry, no refresh rotation.
- [ ] 3. Banking: new backend/app/transfers.py plus schema/database/API tests. Preview binds owner/recipient/amount, conditional intent transition and balance debit in one SQLite transaction. Test double submit, concurrency, rollback, expired intent and cross-user attempts. Expose manual transfer UI and history. Prove day-3 slice.
- [ ] 4. AI: new backend/app/pii.py, graph orchestration, existing agent/tools/gateway. Test read-only allowlist, PII before every model request, mapping isolation, stored injection and result minimization. No arbitrary transfer descriptions to model.
- [ ] 5. QR/UI: camera and uploaded image decoding, strict supported payload parsing, backend revalidation, preview UI. Test malformed QR and real demo device/HTTPS.
- [ ] 6. Verification/report: run configured backend pytest and frontend build/component tests, end-to-end demo, independent review pending if unavailable. Record exact commands and results; no automatic commit/push.

## Ledger
- Latest user instruction supersedes historical STOP entries: fix routine/environment errors and continue; ask only for consequential decisions or difficult-to-reverse operations.
- Follow-up implementation: fail-closed request-local account mapping and 12 binding regression tests; phone monetary-context recognizer with 12/12 fresh synthetic evaluation cases. Full Presidio/model integration remains pending.
- Auth browser acceptance now passed using automatically started isolated Vite/API servers on matching loopback origins.
- Banking manual slice implemented in banking.py/banking_api.py and BankingPanel.tsx: preview/reload/confirm/receipt, ownership, atomic debit/credit, same-intent replay, cancel and history. Concurrent debit and rollback tests passed. Browser validated Alice/Bob balances and recipient history.
- Latest verification: 99 backend tests passed; frontend build and six component groups passed; full browser flow and temporary-server cleanup passed. Independent review pending. Current report: docs/day2-evidence-2026-10-23/completion.md. Tasks 1–3 implemented with recorded limits; tasks 4–5 remain pending and task 6 continues per slice.
- Preflight: existing untracked docs/test-evidence-2026-10-23 and docs/test-evidence-model-2026-10-23 preserved.
- Python 3.11.9; Ollama endpoint reachable, llama3.2:3b Q4_K_M installed. Presidio and LangGraph initially absent.
- Existing chatbot still exposes create_support_ticket (write); must remove from future read-only chat.
- Presidio installation authorized by explicit implementation/trial request; evaluation dependencies kept separate from runtime requirements until integration validated.
- Day-1: 20 native + 20 guarded cases persisted. Native tool 16/20, arguments 15/20; guarded basic checks 19/20. Existing support-ticket write violates new read-only scope.
- Presidio trial: 48 evaluation + 12 development samples, pattern-only; 12/18 applicable binder checks change after naive masking. No production integration performed.
- STOP: benchmark cleanup raises WinError 32 on SQLite temporary DB after all cases. User requested stopping on errors; report saved to docs/day1-evaluation-2026-10-23/REPORT.md. Task 1 evaluation data collected but clean run/verification incomplete; tasks 2–6 not started.
- Resumed on user instruction: removed all chat ticket-tool execution paths; Database.connect closes in finally after commit/rollback. Three new regression tests observed red then green. Historical ticket tests updated for approved read-only behavior.
- Task 1 follow-up: benchmark 20/20 guarded, 15/20 native arguments; cleanup exit 0. PII outcome comparison executes real dispatcher: 11/18 broken vs 12/18 changed. Original evidence untouched. keep_alive=60m configured per request.
- Task 2 implemented: Argon2id seed users, cookie JWT, SQLite revocation, CSRF/Origin/rate limiting, login/logout/reload API and frontend. Removed legacy token API/authentication. New session tests observed red then green.
- Ruling: demo-only HTTP loopback uses explicit AUTH_COOKIE_SECURE=false; default remains true for HTTPS. Generated missing secrets in ignored backend/.env, preserving existing values and database passwords. Credentials not printed.
- Verification: backend 64 passed; frontend build passed; component checks 6 groups passed; isolated live HTTP login/ownership/logout/cleanup passed; git diff --check and browser-script syntax passed.
- STOP: npm run test:identity failed waiting for login/profile because UI :5173 returns ERR_CONNECTION_REFUSED (verified via CDP page text). User asked to stop on errors. No UI login assertion executed; independent review pending. Tasks 3–6 and PII/LangGraph production integration remain pending. Report: docs/day1-followup-2026-10-23/completion.md.
