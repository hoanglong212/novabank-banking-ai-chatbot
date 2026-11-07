# Admin Home implementation plan

**Goal:** turn the sparse Operations overview into a useful, attractive daily banking operations dashboard using actual stored data.
**Architecture:** preserve React/FastAPI/SQLite and existing permissions. Extend `/api/admin/overview` compatibly, isolate its read model in `admin_dashboard.py`, and replace the inline overview with focused Dashboard/TransferChart components and scoped styles. No dependencies, schema changes or simulated revenue/uptime figures.
**Execution:** sequential `msi-aef-executing-plans`; no automatic subagent dispatch. User delegated design choices and requested implementation. Existing English and ivory/violet branding retained.

## Design decision

1. Executive report: large balance/volume KPIs and wide chart, little operational context. Attractive but hides actionable failures.
2. Operations workspace: compact KPIs, transfer-volume chart, attention queue, recent transfers, ledger integrity and recent banking events. Selected because the app has actual transfer, settlement, support and audit records and existing destinations for action.
3. Dense monitoring wall: many small charts/log streams and status lights. Rejected: no infrastructure telemetry source; would imply unsupported monitoring and overwhelm the current MVP.

Use generous but purposeful spacing, four metric columns, a large chart beside the attention queue, a readable recent-transfer table and a compact integrity/audit row. Native sheets for queue/detail inspection. Small restrained entry animation with reduced-motion support. Responsive at 375/768/1440. No fabricated healthy state, percent change, transaction data or inaccessible color-only statuses.

## Data contract and jobs

- Period metrics: unique confirmed transfers, settled volume, successful/failed/pending counts, internal/external volume and previous-period comparison. Derive effective transfer status from settlement state; exclude OTP drafts and avoid double-counting internal account entries.
- Periods 7/30/90 days, Vietnam calendar boundaries and explicit update timestamp. Zero-fill daily series. Success rate excludes pending/draft transfers and is null without terminal outcomes.
- Current snapshot: active customers, payment-account balances, pending settlements, unverified active customers, unresolved support tickets. Label separately from period metrics.
- Work queue: inspect up to 20 current pending and period failed transfers; correct total counts. Open transfer details; navigate to existing transactions/customers/support/audit destinations according to permission.
- Ledger: existing run timestamp, result and mismatch counts, no report means unchecked. Existing authorized reconcile action updates real report; show result/details.
- Recent transfers and banking events: bounded, server sorted, no OTP/secrets or protected support-message bodies.

## Work ledger

- [x] Backend read model + meaningful tests for local-day boundaries, correct status/denominators, zero data, bounded lists and permission enforcement; preserve old overview fields.
- [x] Dashboard component/chart, current-state queues, transfer review, reconciliation, navigation and responsive styles. Keep other admin sections functional.
- [x] Run backend relevant checks, component checks/build, authenticated browser interactions and screenshot review (maximum three assessments/two repair batches).
- [x] Update live local build/backend and completion/API evidence. Preserve unrelated work.

Review focus: stale responses after switching periods; no current-period figures labeled all-time; no pending settlement presented as completed; role-gated mutation actions; no data fabricated to fill empty states; mobile table containment; graceful API failure/retry.

UIUX managed startup was previously rejected by automatic approval review in this session and will not be retried/bypassed. Use standalone audit/QA plus authenticated Playwright captures. Installed Pro Max research supports explicit empty states and named controls; bulk actions are not relevant to this overview. Independent review is not claimed when unavailable.

Implementation and local deployment are verified. Independent review remains pending; see the completion evidence for the limits of this handoff.
