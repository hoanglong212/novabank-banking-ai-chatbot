# M1 account recovery — local implementation evidence, 1 November 2026

The user selected registration, verification and forgotten-password recovery from PDF `(2)`. These flows are implemented and verified locally. **Independent review and remote CI are pending; this is not full M1 completion or release approval.** React/Vite/FastAPI/SQLite, existing design tokens and pre-existing uncommitted work were preserved. No new dependencies/services, commits, pushes or deployment were performed in this increment.

## Acceptance → evidence

| Requirement | Implementation and verification |
| --- | --- |
| Register safely | Strict normalized username/email, Unicode display name, 15–128 character passwords, customer-only role; duplicate registration does not overwrite pending credentials; concurrent duplicate requests create one user/mail |
| Simulated email verification | 256-bit token, SHA-256 storage, purpose binding, 24-hour expiry, resend invalidation; pending login denied; one account with zero VND and ledger mapping created atomically |
| Forgot/reset password | Generic public responses, reset token expires after 15 minutes, single consumption and concurrent replay protection; no automatic login; credential version rejects old JWTs immediately on subsequent authentication |
| Persisted identity | v3 seeds seven original principals once; reset survives repeated startup and does not restore public seed passwords; role permissions read from SQLite |
| Fail safely | Fault-injected account/ledger creation and reset notification failures roll back the whole action; original token can be retried; expiry checked after waiting for the write lock |
| Avoid public inbox exposure | Explicit read-only CLI path, metadata list by default, selected-message disclosure only, loopback origin validation; no HTTP outbox endpoint; consumed links cleared and expired links hidden by CLI |
| Bound public requests | SQLite fixed-window limits per connection peer/action and email/purpose; counters survive startup; generic responses for unknown/pending users; auth validation does not echo passwords |
| Complete UI journey | Real backend Playwright: register → confirm mismatch error → local CLI inbox → verify → sign in → zero balance → forgot → reset → old session rejection → new password login |
| Existing banking behavior | Nine-step Alice–Bob acceptance, customer isolation, receipts, notifications and role checks still pass; new customer can receive a transfer and reconciliation remains balanced |
| Preserve existing data | Migration run twice on a backup of the current working DB: all old values preserved for 3 accounts, 11 transactions, 2 transfers, 83 conversations, 341 messages, 177 tool events and 16 tickets; source hash unchanged during verification; ledger balanced |
| Responsive/accessibility behavior | Named inputs, password hints separate from accessible labels, focus moves to new form headings, errors/status announced; 375/768/1440 browser checks and inspected screenshots |

## Actual commands and outcomes

- `backend/.venv/Scripts/python.exe -m pytest -q` → **185 passed in 63.11s**, exit 0. Adds 25 lifecycle tests (including parameterized cases) and 2 CLI tests to the prior 158 tests.
- In `frontend`, `npm run test:components` → **13 groups passed**, exit 0.
- In `frontend`, `npm run test:e2e` → TypeScript/Vite production build passed; **7 Playwright tests passed in 43.3s**, exit 0. Uses a fresh isolated DB at port 8092; financial/auth requests use the real backend. Only the unrelated external bank list is stubbed.
- `backend/.venv/Scripts/python.exe scripts/reconcile.py --db <latest isolated E2E DB>` → exit 0; `balanced=true`, `ledger_total_vnd=0`, no mismatches or unbalanced journals.
- `backend/.venv/Scripts/python.exe .local/verify-identity-migration.py` → old data preserved, migration versions 1/2/3 present, source file hash unchanged, reconciliation passed. This is a copy verification, not an in-place reset of the working DB.
- `uiux audit --target frontend` → exit 0; three static warnings from the React HTML shell/generated Playwright report. Static HTML heuristics do not assess React forms or constitute a WCAG pass.
- `uiux qa --url http://127.0.0.1:8093 --out .local/uiux-identity-readonly` → all machine checks passed at 375×812, 768×1024 and 1440×900: no runtime errors, horizontal overflow, unnamed buttons or missing heading. Uses a copied test DB.
- Visual self-review opened **12 PNGs** across login/register/forgot/reset/error states. Eleven accepted; one mobile reset image caught an entrance animation and was replaced by a capture waiting for fonts/finite animations. Two assessment sets, no UI repair loop. SHA-256 hashes and findings are recorded in `.local/identity-verification/visual-review.json`.
- `git diff --check` → exit 0; only repository LF/CRLF conversion notices.

The backend suite was rerun after the final expiry fix. The focused regression first failed, then both verification/reset cases passed after moving the clock read inside the acquired transaction. Earlier TDD red states also showed missing lifecycle routes (404), missing inbox script, and missing registration entry point. Browser testing found hint/button text polluting input accessible names; `aria-labelledby` corrected the forms and the complete suite then passed.

Evidence paths are local/ignored: `.local/backups/novabank-before-identity-2026-11-01-60b1e33c.sqlite3`, `.local/identity-verification/`, `.local/uiux-identity-readonly/`, `.local/e2e/`, and `frontend/test-results/`. Test DBs/traces contain synthetic credentials or development tokens and are not committed. The temporary QA server was stopped after checks.

## Changed areas and review

- Backend: new `identity_schema.py`, `identity_schemas.py`, `identity.py`, `routes_identity.py`; adapted `database.py`, `auth.py`, `main.py`; lifecycle/CLI regression tests.
- Frontend: shared `AuthShell`, `AuthFlow`, fragment parser, login entry points, API methods, App action-link handling, scoped auth styles; component and browser tests.
- Operations/docs: read-only `scripts/dev-outbox.py`, [usage/rules](ACCOUNT_RECOVERY_VI.md), README, scope/alignment/architecture/security notes and checked execution plan.
- Primary agent performed self-review of transaction/expiry/replay boundaries, role/ownership, migrations, token exposure, UI states and compatibility. **No independent reviewer was dispatched; independent review remains pending.** The local msi-aef adaptation requires an authorized reviewer/human and pending status when unavailable; this self-review is not substituted for that gate.

## Remaining limits

- Full M1 still needs login MFA, refresh rotation, per-session management/idle timeout, logged-in password change with OTP and Security Center. Existing login lockout remains in memory (five attempts/five minutes).
- Outbox is local simulated mail, not proof of ownership of a real mailbox. Anyone able to read the DB can access reset links, including staff seed links. Raw outbox URLs remain until consumed/replaced; no expired-message retention job. Request/delivery rate limits use fixed windows, not a production abuse-control service.
- Generic responses/hash work reduce obvious differences but are not constant-time guarantees. Email format validation is intentionally bounded/basic; no SMTP, multi-instance/load or production identity assurance was tested.
- Remote GitHub checks have not run. Existing `checks.yml` will include these tests when the branch is published. No `engineering.json`, lint/format gate or independent security audit is configured; repository checks were used directly.
- Prior dependency audit still records two moderate development-tool findings (Vite and postcss-selector-parser); no dependencies changed in this increment. Real-model injection robustness and full M2 are outside this selected work.
- The managed UIUX coordinator was blocked by automatic tool policy in the preceding increment. This continuation used read-only QA plus browser captures, and makes no managed-coordinator completion claim.

## Rollback and use

Restart the backend to apply migration v3; the UI build is ready. Follow [ACCOUNT_RECOVERY_VI.md](ACCOUNT_RECOVERY_VI.md) to read local messages. Resetting a demo seed password intentionally makes its old autofill credentials stop working; startup preserves the new password.

For rollback, stop the app and first preserve a fresh complete DB backup. Restore matching application code and a known pre-migration backup together, after reviewing data created since that backup. Restoring an older DB discards newer identities and financial/chat changes. Do not drop identity tables or delete the live DB to undo this increment. No rollback was executed.
