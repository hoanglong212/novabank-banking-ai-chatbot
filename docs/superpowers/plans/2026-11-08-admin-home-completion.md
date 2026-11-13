# Admin Home implementation evidence

Date: 2026-11-08. Implementation and existing local deployment updated; independent review pending. English UI, ivory/violet tokens, existing stack and permissions preserved. No packages or services installed; no migrations.

## Acceptance and evidence

| Requirement | Evidence |
|---|---|
| Useful operating overview | Four metrics, 7/30/90-day chart, pending/failed/support/verification attention list, recent transfers, ledger integrity, recent banking events |
| Actual stored data and correct periods | New SQL read model; backend tests cover Vietnam boundary, unique transfer volumes, terminal-only success denominator, pending snapshots, empty values and bounded queues |
| Working actions | Authenticated browser tests open transfer/audit and queue sheets, switch periods, run reconciliation, inspect report, navigate transactions/customers/support, retry failed API request |
| Permissions | Customer overview denied; auditor read allowed and reconciliation denied; auditor UI omits mutation control |
| Responsive | Authenticated captures and root-overflow assertions at 375/768/1440; mobile table rows, readable chart and review sheet inspected |
| Existing local app updated | Existing launcher restarted hidden with same database/config; health and ready returned 200; served `/admin` references index-Dh6vTK9j.js and current dashboard text |

## Changed files

- `backend/app/admin_dashboard.py`, `backend/app/routes_admin.py`: additive overview contract and snapshot read model.
- `backend/tests/test_admin_dashboard.py`: focused metric/permission tests.
- `frontend/src/components/admin/{AdminConsole,Dashboard,TransferChart,dashboardTypes,Operations}.tsx` (types file uses `.ts`): dashboard, chart, shared audit export and integration.
- `frontend/src/styles/admin-dashboard.css`: scoped responsive styles and motion/reduced motion.
- `frontend/tests/e2e/admin-dashboard.spec.ts`: authenticated acceptance flows and isolated fixture timing.
- API specification and implementation/completion plan files.

## Executed checks

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_admin_dashboard.py backend/tests/test_services.py backend/tests/test_core_experience.py backend/tests/test_SEC_01.py -q --tb=short`: **45 passed** (16.55 s). Observed meaningful RED then GREEN for new read model.
- Frontend `npm run test:components`: **18 configured PASS results**, exit 0.
- Frontend `npm run build`: **passed**, TypeScript/Vite; final application bundle `index-Dh6vTK9j.js`, stylesheet `index-bGeVA7tl.css`.
- Frontend `node node_modules/@playwright/test/cli.js test --config .local/qr-pay-tests/admin-config.mjs`: **3 passed**, exit 0, after final application changes. Uses existing disposable local harness on 8098, adapted test path, production assets and no working database. Screenshot evidence: `.local/admin-home/*.png`; output: `browser-final.txt`.
- Final fixture portability recheck: **3 passed** (36.2 s), exit 0; `browser-portable.txt` (no application edits).
- Relevant `git diff --check`: passed.

## Visual assessment and limits

Three visual assessments / two repair batches used. Repairs addressed mobile table containment, escaped screen-reader header geometry, page selector specificity, compact feedback, long references, external recipient fallback and clearer metric/date semantics. Final assessment inspected desktop overview/footer, mobile chart/activity/review and tablet chart. A minor punctuation artifact remains between failed count and pending-exclusion text; it does not affect metrics or controls.

Standalone UIUX audit/QA was executed; CLI screenshots were unauthenticated and therefore supplemented with authenticated Playwright captures. CLI QA overall is not passing because the existing intro animation fetch reports `net::ERR_ABORTED` during cleanup. The current admin browser flow reported no page errors. Managed UIUX startup had been blocked by automatic approval review; it was not retried or bypassed. This is not a WCAG certification or an all-repository regression claim.

Independent reviewer identity/result: **pending / unavailable under the current sequential local workflow**. Self-review covered status/date semantics, parameter binding, permissions, bounded payloads and stale-period response display; it is not independent review. The implementation is available for use, while the independent review process gate remains open.

## Operations and rollback

Data is simulated banking data; no real bank transfer/provider was added. Dashboard is a timestamped manual-refresh snapshot, not live infrastructure telemetry. Live local database was not used by acceptance fixture transfers or reconciliation.

To roll back, revert only the Admin Home-specific hunks and new files listed above, preserving unrelated current changes. Rebuild the existing frontend and restart the existing local launcher with its current environment/database. No schema rollback or data deletion is needed.
