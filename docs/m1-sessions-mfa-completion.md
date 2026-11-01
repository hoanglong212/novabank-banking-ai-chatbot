# M1 sessions and MFA — verified local continuation, 1 November 2026

The user asked to continue after the PDF/code audit found broken login: backend `/auth/login` returned an MFA challenge, while the frontend still treated it as a token. The existing v4 backend was retained and connected to the UI. **Implementation is verified locally; independent review and remote CI remain pending. This does not complete the whole M1/M2 or research roadmap.**

## Acceptance → evidence

| Requirement | Implementation / actual verification |
| --- | --- |
| No authenticated UI before MFA | Separate challenge/session types; password login opens `MfaSignIn`; wrong code leaves browser credentials empty; successful email/TOTP verification opens the app. Backend tests verify action binding, expiry, replay and concurrent consumption. |
| Working banking after login change | All existing browser sign-in helpers now complete real local email MFA. The nine-step Alice–Bob transfer, history/PDF, notifications, admin audit and third-user isolation pass again. |
| Session coordination | `sessionStore.ts` keeps per-tab credentials, deduplicates rotation, preserves the user reference and rejects late responses after logout/new login. Component checks cover concurrent rotation, stale refresh/401 responses, identity binding, activity throttle and wall-clock idle/absolute expiry. |
| Real backend revocation and refresh | Browser test restores expired access metadata, observes a rotated refresh credential with unchanged user/session/idle deadline, signs out and confirms both old access and refresh are rejected. A separate browser session becomes unusable after Security Center revocation. |
| Security Center and factor lifecycle | Profile shows active sessions, paginated login history, TOTP setup/disable and email fallback. Chromium completes setup, authenticator login, fallback, password + separate email confirmation to disable, and rejection of another revoked session. Setup keys are cleared on close/expiry and masked in the saved mobile screenshot. |
| Account lifecycle remains usable | Browser registers, verifies, completes MFA with a zero-balance account, receives 100,000 VND from Alice, sees the notification/balance, resets the password and proves old credentials are rejected. |
| Existing data preserved | Read-only SQLite backup before edits; initialize a copy twice through schema versions 1–4. All old columns/rows preserved; original DB hash unchanged; reconciliation balanced. No working DB reset or migration was performed. |

## Commands and results

Run from repository root except frontend commands:

- `backend/.venv/Scripts/python.exe -m pytest -q` → **198 passed in 78.49s**. Real temporary SQLite; mock/fake model tests, not a live LLM evaluation.
- `cd frontend; npm run test:components` → **14 groups passed**. Includes transfer retry headers and the new session coordinator cases.
- `cd frontend; npm run test:e2e` → TypeScript/Vite build passed; **10 Chromium tests passed (1.0m)** in the final full run. The disposable launcher owns its DB and server at port 8092.
- `backend/.venv/Scripts/python.exe .local/m1-sessions-continuation/verify_migration.py` → exit 0. Preserved 83 conversations, 341 messages, 177 tool events, 16 tickets, 3 accounts, 11 transactions, 2 transfers and all existing ledger/detail rows; versions `[1,2,3,4]`, original unchanged, global ledger 0.
- `backend/.venv/Scripts/python.exe scripts/reconcile.py --db <latest isolated E2E database>` → exit 0, `balanced=true`, `ledger_total_vnd=0`, no mismatches/unbalanced journals.
- `git diff --check` → exit 0; only existing Windows LF/CRLF conversion notices.
- `node C:/Users/Admin/Documents/AI-Engineering/Framework/aef.mjs check .` → exit 1 / ENOENT for `engineering.json`: framework gates **not configured**. Repository commands above were run directly. No framework initialization or dependency installation.

The initial audit had 3 passing / 5 failing browser tests and component bundling failed because `sessionStore` did not exist. After login integration, a targeted browser test failed at the absent Security Center before that component was implemented. The first full run then exposed two test issues: a shared user already had a prior session, and Sign out matched both navigation and Profile. Test identities/locators were corrected without weakening the revocation assertions. The subsequent full suite passed; final screenshots and wrong-code assertions also passed.

Evidence: `.local/m1-sessions-continuation/{backend.log,components.log,e2e-final.log,migration-result.json,visual-review.json,continuation.diff}` and `frontend/test-results/`. Logs/traces and DB/key backups remain ignored. Browser captures of mobile MFA, mobile Security Center, desktop sessions/history, masked mobile TOTP setup and enabled status were opened and visually inspected. These capture scrolled portions of the application shell; they are not a full WCAG audit. Mobile overflow assertions passed.

## Changed areas and operation

- New frontend session coordinator; updated authenticated API client, auth hook, app session key and response types.
- New MFA screen and Profile security/factor components; reused existing auth shell, native dialog sheets and design tokens.
- Component/session checks and banking/identity/security browser scenarios; no test-only authentication bypass or inbox HTTP route.
- Existing backend MFA/session modules passed their suite; this continuation did not rewrite their behavior. The JWT restart comment and `.env.example` now reflect the fixed five-minute JWT/refresh model.
- Dockerfile packages the existing outbox CLI so an operator can retrieve local MFA codes. Docker build/runtime were **not executed** in this turn; no image/dependency pull was initiated.
- README, scope, architecture, security/business rules and operating guides updated. The historical static-token `scripts/check-demo.py` is explicitly retired from the current acceptance instructions.

Restart a previously running backend to load v4 auth routes/migrations, then reload the newly built frontend. Old JWTs without session IDs need a new sign-in. See [MFA/session instructions](SESSIONS_MFA_VI.md), including the local inbox and Docker commands. Back up `<DB_PATH>.mfa.key` (or the configured Fernet key) with any DB containing authenticator settings.

## Review, limits and remaining work

Reviewer: **Codex self-review**, using the existing plan's five review-focus items and the code-review template. Checked challenge-to-session transition, server-only authorization, refresh/late-response boundaries, activity/idle behavior, setup-secret lifetime, component cleanup, migration preservation and test fixtures. One test fixture was corrected during review so its identity-mismatch response had valid future expiry and genuinely exercised identity binding. No known critical/important finding remains in the implemented scope. Independent reviewer: **none; pending**. The existing plan explicitly calls for inline execution without subagents.

The [documentation skill](C:/Users/Admin/.agents/skills/msi-aef-documentation/SKILL.md) states: “Completion requires configured checks passed and required independent review resolved; otherwise report partial completion.” Accordingly this is verified implementation with review pending, not merge/release approval.

Remote GitHub CI, Docker, load/coverage measurement and real-model research were not run. No standalone lint or dependency-security gate is configured. Existing dependency advisories remain separate work. Email and device notices are local simulation; the readable outbox and per-tab bearer storage are not production security assurance. Duplicate browser tabs can copy a session's credentials; use separate sign-ins for independent sessions. Expired mail cleanup is still pending.

Remaining M1: profile editing/reverification and password change with action-bound OTP. Remaining M2: beneficiaries, asynchronous interbank settlement/reversal, periodic reconciliation and internal QR. M3–M6 remain as listed in [Build Scope](BUILD_SCOPE_VI.md).

## Rollback

No commit/push/tag was made. The branch contains earlier uncommitted work, so do not reset the branch wholesale. A task-start source snapshot and DB backup are in `.local/m1-sessions-continuation/before/` and `before.sqlite3`; use them to review/revert only this continuation's changes. Keep the frontend/backend auth contract together. Before changing a running database, stop the affected process and preserve later transactions. Restore a chosen backup to a separate path for validation, with its matching code and encryption key; restoring the old backup over current data would discard later work.
