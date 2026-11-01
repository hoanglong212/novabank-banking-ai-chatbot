> Historical milestone record. Current implementation and evidence: [STATUS](release/STATUS.md). On 2026-11-01 the user confirmed local-only delivery. The local implementation is verified; public hosting and remote release are outside the current scope. Historical test counts and pending milestones below do not supersede STATUS.

> Post-audit fixes: [10 requested cases, 4 specification decisions, verification and rollback](release/acceptance-fixes/REPORT_VI.md). Final checks: 271 pytest, 17 component groups, 15 E2E, balanced reconciliation; 93.58% financial executed-line coverage. Self-review completed; independent review remains pending. AI-14/PI-05/PI-06 deferred by the user. No demo database writes, dependency installations, commits, pushes or demo-server restart in this fix pass.

> Latest acceptance audit against the newly supplied 121-case PDF found missing features and contract differences: [findings and evidence](release/acceptance-audit/REPORT_VI.md). This audit supersedes any blanket completeness claim; implementation code was not changed during the audit.

# Core experience — implementation and verification, 1 November 2026

**Latest continuation:** MFA login, refresh/session coordination and Profile Security Center are verified in [M1 sessions/MFA evidence](m1-sessions-mfa-completion.md): 198 backend tests, 14 frontend groups, build and 10 browser tests pass locally. Independent review/remote CI remain pending. The earlier [account recovery evidence](m1-account-recovery-completion.md) and the core-experience record below retain their historical test counts.

Implemented the updated PDF's steps 5–7 and exercised its complete nine-step Alice–Bob scenario. **Implementation verified locally; independent review and the broader M1/M2 milestones remain pending.** User-approved stack and pre-existing uncommitted UI work were preserved. No commit, push, tag or deployment was made.

## Acceptance → evidence

| Requirement | Implementation and actual evidence |
| --- | --- |
| Owned history, filters, paging | `banking_queries.py`, `routes_banking.py`, Activity; owner isolation, literal search, date/status/direction/bounds and pagination API tests; browser search by reference |
| Stable detail/receipt | v2 immutable snapshots for payer/recipient; ReportLab PDF; tests verify stable balance/bytes after another transfer, completed-only ownership and no-store; actual PDF download in browser |
| Notification Center | Atomic posting notifications, unique owner/transaction, read/read-all, visible-page polling; tests for rollback/replay, cross-owner reads, persistence; Bob browser alert/read/reload |
| Minimum RBAC/admin | Server-owned five-role permission matrix; Operations/auditor/admin financial reads; customer/support denied; staff customer APIs denied; forged role claim test; admin browser search/audit |
| Alice 10m → 8m, Bob +2m | Real backend/browser scenario in disposable DB; balances asserted, replay/insufficient funds checked; CLI reconciliation `balanced=true`, global ledger total 0 |
| Third-user isolation | Charlie authenticates in a separate browser context; both customer receipt/detail endpoints return 404; admin returns 403; own history remains empty |
| Preserve data during upgrade | SQLite backup and migration on a copy of working DB; all old values preserved: 2 accounts, 11 transactions, 2 transfers, 82 conversations, 339 messages, 176 tool events, 16 tickets. Original file hash unchanged; reconciliation passed. Automated v1→v2 backfill test also passes |
| Mobile/tablet usability | Browser tests at 375×812 and 768×1024; visual capture also at 1440×900. Tablet navigation gained explicit accessible names; long mobile references now stay inside their row |
| Honest totals | Existing “This month” label incorrectly summed all dates and pending entries. Changed to “Completed activity” and exclude pending/failed; regression was observed failing before the fix |

## Actual commands and results

Commands run from repo root unless noted:

- `backend/.venv/Scripts/python.exe -m pytest -q` → **158 passed in 47.12s**. Includes 22 experience tests plus previous foundation/agent suites.
- In `frontend`: `npm run test:components` → **12 groups passed**.
- In `frontend`: `npm run test:e2e` → production TypeScript/Vite build passed; **3 Playwright tests passed in 24.1s**. One test covers all nine acceptance steps; two cover mobile/tablet history/receipt/alerts.
- `backend/.venv/Scripts/python.exe scripts/reconcile.py --db <isolated-E2E-DB>` → **exit 0**, `balanced=true`, `ledger_total_vnd=0`, no mismatches/unbalanced journals.
- `backend/.venv/Scripts/python.exe .local/verify-experience.py` → working DB copy migration preserved old data and original hash; reconciliation passed; Unicode PDF generated.
- `pdftoppm -scale-to 1200 -png -singlefile .local/experience-verification/vietnamese-receipt.pdf ...` → rendered PDF opened and inspected: Vietnamese accents, literal markup, long reference, fees and recorded balance legible on one page.
- `uiux audit --target frontend --json` → exit 0; heading warnings from static HTML shell/artifacts (React renders headings at runtime); this heuristic is not a rendered audit.
- `uiux qa --target frontend --config-dir .local/uiux-config --url http://127.0.0.1:8093 --out .local/uiux-core-experience-readonly --json` → **12/12 scenarios/viewport combinations passed machine checks**, no runtime errors, horizontal page overflow, unnamed buttons or missing alt attributes.
- Coordinator `uiux run start ...` was rejected by automatic tool policy with **“blocked by policy”**. It was not retried with equivalent invocation. Read-only `uiux qa` and local Playwright captures provided the fallback evidence; no managed coordinator “complete” state is claimed.
- The first CLI screenshots caught animation transitions, so those images alone were not accepted visually. A read-only capture waited for finite animations/fonts, and a final capture after the bounded repair batch was made in `.local/uiux-final/`. At most three visual assessment sets were used; no automatic repair loop.
- All **12 final PNGs were opened and visually inspected**; their SHA256 values and the attributable self-review are saved in `.local/uiux-final/visual-review.json`. Final DOM/runtime assertions passed for all 12 captures. Operations screenshots intentionally scroll the sheet to its audit trail; the amount is available above in the same scrollable content. The actual browser-downloaded Alice PDF was also rendered and visually inspected.
- `git diff --check` → exit 0 (only repository LF/CRLF conversion notices).
- `node C:/Users/Admin/Documents/AI-Engineering/Framework/aef.mjs check .` → **not configured**: repository has no `engineering.json`. Per router instructions, actual repository commands above were run directly; the project was not initialized.
- `npm audit --json` → **2 moderate findings**, Vite 6.4.4 and transitive postcss-selector-parser <6.1.5. Not fixed by an unrelated blanket dependency upgrade.

Evidence is local/ignored: `.local/backups/novabank-before-experience-2026-11-01-3239eea9.sqlite3`, `.local/experience-verification/`, `.local/e2e/`, `.local/uiux-final/` and `frontend/test-results/`. Browser traces may contain demo tokens; they are not committed. Local runtime: backend virtualenv Python 3.14, Node 24.15; CI is configured for Python 3.12/Node 22 but has not run remotely.

## Changed areas and operational notes

- Backend: shared auth/permission dependencies, schema v2 and atomic detail/notification writes, filtered read APIs, PDF renderer/font+license, role-aware login/me, tests. ReportLab was explicitly approved by the user.
- Frontend: role-aware navigation, Activity filters/pagination, receipt sheets/download, Alerts, Operations/audit, reusable request/query hooks and styles. Playwright dependency, isolated launcher/config/scenario were explicitly approved.
- CI: `.github/workflows/checks.yml` runs pytest, component checks, build/E2E and failure artifacts. CI file presence is not evidence of a remote pass.
- Documentation: updated plan alignment/business rules/architecture/security; added [25-function scope](BUILD_SCOPE_VI.md). Remainder of roadmap is explicit there.
- Restart the existing backend to apply migrations and load new endpoints; production static serving uses the freshly built `frontend/dist`. No running user server or working DB was reset during implementation.

## Review and remaining limits

Self-review: Codex inspected migration/backfill, permission enforcement, query parameterization, rollback/idempotency, PDF escaping and UI loading/error behavior. Independent reviewer: **none; pending**, so this is not a merge/release approval.

The [local documentation skill](C:/Users/Admin/.agents/skills/msi-aef-documentation/SKILL.md) requires: “Completion requires configured checks passed and required independent review resolved; otherwise report partial completion.” This record therefore reports verified implementation with review pending, not full milestone completion.

Remaining: M1 registration/verify/reset/MFA/session lifecycle/login history; beneficiary management, asynchronous simulated interbank/reversal, periodic reconciliation and offline QR; remaining M3–M6 products/research. Browser checks use the real banking backend with mock AI, not a live model. No Docker execution, load tests, financial coverage threshold measurement, remote CI, full WCAG certification or real-model prompt-injection safety claim. Lint and dependency-security CI gates are not configured. `/api/me` still returns the existing full demo history; future large-data work should split dashboard aggregates from the paginated history API.

## Rollback

Stop the affected local backend before restoring data. Preserve any post-upgrade transactions first. Restore a chosen pre-upgrade backup to a separate file and point `DB_PATH` to it for validation, then run the matching previous code. Do not drop immutable ledger/detail tables or rewrite balances to force a downgrade. Rolling back to this turn's backup would discard all later activity, so it must be a deliberate choice. For code rollback, revert only this increment's reviewed diff; the branch also contains earlier user UI changes and foundation work, so a blanket reset is inappropriate.
