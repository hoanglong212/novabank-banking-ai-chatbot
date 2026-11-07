# Explore services implementation plan

Goal: redesign all nine Explore services and finish usable end-to-end simulated banking flows, preserving real persistence, ownership checks, OTP and ledger protections.

Architecture: retain React/TypeScript, existing FastAPI endpoints, npm, styles/tokens and native Sheet. Separate cards, bills, savings, goals and statements into focused components. Reuse loading/error/form primitives and existing QR Pay. No dependency installation, real payment integration or account migration.

Design directions: (1) nine uniform dashboard cards, (2) searchable service directory grouped by user tasks, with individual workspaces and focused action sheets, (3) a conversational service launcher. Choose (2): users can find a task quickly and see actual balances/status/history without an assistant conversation or a wall of forms. Preserve ivory/violet, large headings, thin dividers, purposeful card visuals and restrained motion; support reduced motion and keyboard navigation. This task uses the user's existing visual preferences. The user confirmed English. All new Explore copy stays English; the existing shared QR flow retains its prior Vietnamese copy.

## Work ledger

- [x] Shared directory/navigation, reusable visual states, action feedback and responsive styles. Directory search/groups and return navigation must work.
- [x] Accounts: readable balances/details, rename/copy, recipient search/add/edit/remove/transfer; restore bank catalog selection with simulated external recipient lookup.
- [x] Cards: debit/credit visuals, status, available credit, freeze/unfreeze, purchase/repayment sheets, OTP, persistent history; frozen purchases disabled.
- [x] Bills: category/status filters, due totals, bill details, reminder setting, payment account selection, OTP and paid state.
- [x] Savings: active/closed deposits, backend-supplied rates, opening projection and source balance, OTP opening/withdrawal, maturity details/history.
- [x] Insights: month income/spending/net, categories/daily values, editable persistent budgets and progress states.
- [x] Goals/calculators: create/edit/link/delete goals, real linked progress, bounded savings and loan calculators. Add owner-scoped goal-update endpoint and regression coverage.
- [x] Statements: quick periods, range validation, PDF/CSV downloads and clear success/error.
- [x] Support/help: ticket creation/list/filter/detail/reply/attachments, staff responses, searchable knowledge and clear empty states. Keep staff workflows compatible.
- [x] QR: retain scan-first camera/OCR/receive behavior in Explore, avoid nested duplicate headings.
- [x] Verify actual backend checks, component checks, build and authenticated desktop/mobile browser flows; inspect captures, update deployment and completion evidence.

Review focus: duplicate submissions; stale modal responses; frozen/closed resources; account ownership; empty accounts/banks; month/date/amount bounds; staff/customer support permissions; mobile modal scrolling/focus. Local implementation review completed; independent review remains pending and is not claimed. No agents dispatched.

UIUX managed run has previously been blocked by automatic approval review in this session; do not retry/bypass. Use permitted standalone audit/QA and authenticated Playwright captures, recording the limitation. Maximum three visual assessments/two repair batches for this redesign.
