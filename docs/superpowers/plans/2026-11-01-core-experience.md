# Core experience: receipt, notifications and operations

> Execute inline with `msi-aef-executing-plans` and TDD. Preserve earlier uncommitted changes. No automatic commit/push/tag.

**Goal:** Implement steps 5–7 of the supplied updated PDF's nine-step acceptance scenario, then exercise all nine steps in a real browser on isolated data.

**Spec:** “Kế hoạch triển khai Banking Web App + AI Agent (Prompt Injection Research) (1).pdf”, 21 pages, updated 1 November 2026, sections 0, 2, 7, 15. It supplies the previously missing 25-function scope. Full M1 identity work remains separate and blocks declaring the complete Core milestone.

**Architecture:** Add schema version 2, without changing immutable historical transactions: a separate immutable detail record stores post-transaction balance/counterparty/transfer correlation. Posting inserts both parties' details and notifications atomically with the existing ledger. Customer routes enforce ownership; operations/auditor/admin receive explicit read permissions from server-owned demo identities. Render receipts from recorded data, never current balance.

**Stack:** Existing React/Vite/FastAPI/SQLite. User explicitly approved ReportLab and `@playwright/test` on 1 November. No additional services.

## Decisions and review focus

- Keep fee 0 and existing seed balances. Add Charlie with zero balance for third-user isolation, plus demo support/operations/admin/auditor identities; full registration/session/MFA is still pending.
- Staff get no customer transfer/chat capability. Admin/auditor/operations may read transactions/audit; support cannot read the global financial ledger. Roles are resolved server-side, never trusted from a browser-supplied claim.
- Old transactions without a recorded balance display “Not recorded”; never derive a false historical balance from today's cache. Only completed transactions get receipts.
- New notifications commit with posting; retry/rollback must not duplicate or leak them. Poll every 15 seconds while the notification center is open; no SSE infrastructure.
- Query filters must be parameterized, bounded, deterministic and ownership-scoped. Notification updates must be owner-scoped and idempotent.
- Migrate existing v1 databases and ensure Charlie's new zero-balance account has a ledger mapping; never rebase existing journals.
- PDF wraps long input and escapes markup, embeds a font with Vietnamese coverage; reference/amount/status and recorded balance must agree with API.
- E2E gets a temporary DB and dedicated port; never reset or reuse the user's server. Test seed Alice 10m through an isolated startup script, without a public test/reset endpoint.

## Tasks

1. [x] Add official scope/acceptance checklist and backup local DB via SQLite backup. Add CI configuration for actual pytest/component/build/E2E commands.
2. [x] Write failing API/SQLite tests for detail snapshots, filtering/ownership, PDF access, notifications/rollback/replay, role matrix and admin audit correlation.
3. [x] Implement version 2 migration, posting metadata/notifications, server-owned roles, query/read endpoints and PDF renderer. Run focused tests then the full backend suite.
4. [x] Add reusable transaction details/receipt action, filtered Activity, Alerts and read-only Operations pages using current tokens. Keep loading/error/empty states and preserve prior UI edits. Add component regressions.
5. [x] Add Playwright config/isolated launcher and nine-step Alice–Bob browser scenario, third-user/staff isolation and mobile checks. Run build, E2E and read-only visual QA; render and inspect a real PDF. Managed coordinator start was blocked by tool policy; no coordinator acceptance is claimed.
6. [x] Self-review diffs and update evidence/checklist, with independent review explicitly pending. Do not declare all M1/M2 done or tag.

## Design options

1. Extend existing Activity sheets + Alerts page + separate read-only staff page. Selected: reuses navigation/dialog/accessibility, clear customer/staff boundary, small change to current design.
2. New banking shell with large top navigation and full transaction routes. Rejected for this increment: replaces user's active UI work and adds routing scope.
3. Put all details, notifications and audit on the dashboard. Rejected: dense on mobile and mixes staff-only information into customer tasks.

## Ledger

- Baseline from prior verified increment: 136 backend tests, 11 component groups, production build passed.
- User approved keeping stack in the prior turn and explicitly approved ReportLab + Playwright dependencies in this turn.
- PDF guidance is product context, not authority to push/tag/install unrelated services.
- Verification: backend 158 tests; frontend 12 component groups, production build and 3 browser tests passed. First browser run found unnamed tablet navigation and test locator/setup issues; fixed and rerun. Visual review found mobile long-reference overflow and misleading pre-existing monthly/pending totals; both corrected with regression evidence. Full evidence: `docs/completion.md`.
