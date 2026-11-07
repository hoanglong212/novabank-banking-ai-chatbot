# Explore services implementation evidence

Implemented on 2026-11-08. The new directory and service workspaces retain English, ivory surfaces and violet tokens. The existing shared Vietnamese QR Pay flow remains intact. No packages or services were installed.

## Acceptance and evidence

| Service | Working behavior | Evidence |
| --- | --- | --- |
| Directory | Search nine services, grouped navigation, empty search, return navigation, reduced motion | Authenticated desktop 1440px and mobile 375px browser test; captures in `.local/explore` |
| Accounts | Balances, copy ID, rename; VietQR bank selection; save/search/edit/remove recipient; prefilled transfer | Browser rename persistence, recipient edit/remove/transfer; backend catalog and ownership checks |
| Cards | Debit/credit visuals, available credit, freeze/unfreeze, purchase, credit repayment, history | Browser OTP purchase/repayment and freeze/unfreeze; existing product invariants |
| Bills | Category/status filters, amount due, reminders, review, account selection, OTP payment, paid details | Browser bill payment and paid state; backend duplicate/payment invariants |
| Savings | Backend rates, deposit projection, opening, active/closed views, early withdrawal, history | Browser opening/withdrawal and linked deposit; backend accounting invariants |
| Spending | Month totals, categories, daily breakdown, editable budgets | Browser create/edit/reload budget; backend insights tests |
| Goals | Create/edit/link/remove; progress from owned active savings; savings/loan calculators | Browser 50% linked progress, edit persistence and deposit retained after goal removal; backend ownership/date checks; calculator component checks |
| Statements | Quick periods, valid date bounds, PDF and CSV downloads | Browser invalid range disabled, PDF and CSV downloads; backend statement tests |
| Help/support | Create/filter/open tickets, replies, attachments/download, staff responses, searchable help library | Mobile browser ticket/file download/staff reply; backend attachment isolation and status filtering |
| QR | Existing scan-first flow and personal QR preserved; duplicate nested heading hidden inside Explore | Mobile signed QR receive/read flow; both responsive layouts inspected |

Financial operations use the existing simulated ledger and confirmation endpoints. No real payment, card, utility or savings provider integration is claimed. External bank recipient names are explicitly simulated. Budget and goal data persist in the backend, not browser-only storage.

## Checks run

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_explore_completion.py backend/tests/test_services.py backend/tests/test_product_invariants.py backend/tests/test_SEC_01.py -q --tb=short`: **29 passed**. New goal-update and catalog-recipient tests were observed failing before implementation, then passing.
- From `frontend`, `npm run test:components`: all configured component/API/calculator checks passed.
- From `frontend`, `npm run build`: TypeScript and Vite production build passed. Served assets include `index-Cky4xipg.js` and `index-DZvwhDVI.css` at verification time.
- From `frontend`, `node node_modules/@playwright/test/cli.js test --config .local/qr-pay-tests/explore-config.mjs`: **5 passed**, final Playwright `.last-run.json` reports `passed` with no failed tests. Runs use copied source specs and an isolated disposable database/backend on port 8098. PowerShell's redirected wrapper reported NativeCommandError for web-server stderr despite the successful Playwright report; this is not represented as a clean wrapper exit.
- First browser failures were test-locator assumptions: the savings amount appears in its history too, and closing a transfer returns to Home. Assertions/navigation were updated to the actual UI behavior.
- Visual review: initial captures caught enter animations; subsequent reduced-motion captures showed the completed layouts. Fixed card details extending beyond the card edge, removed duplicate QR headings and added mobile bottom spacing. Final card and support-sheet captures inspected; card width now has a browser regression assertion. No page errors or page-level horizontal overflow in the nine-service render test.

## Local deployment

Rebuilt `frontend/dist` and restarted the existing `.local/local-deploy/start.ps1` launcher with its existing database and Ollama configuration. `/api/health` and `/api/ready` returned 200; the served bundle includes the new Explore implementation. Restarted the existing Vite process on 5173 after diagnosing a stale `Welcome` module export in its module cache. A fresh browser then reached the login form with no page errors.

## Scope of review and limitations

- Implementation review performed locally: owner checks, bound SQL parameters, duplicate submission guard, stale month data, frozen card controls, active savings links, attachment permissions and existing TOTP/email confirmation compatibility were inspected. Independent review remains pending; no independent reviewer was dispatched or claimed.
- Standalone UIUX static audit completed with heuristic warnings, predominantly generated HTML/browser-profile files and the SPA shell. Standalone UIUX browser QA initially timed out on the stale Vite module, subsequently diagnosed and resolved as above. No managed UIUX gate pass is claimed; managed run startup had previously been blocked by automatic approval review and was not retried or bypassed.
- Authenticated screenshots cover the actual built service UI. They do not certify full WCAG compliance or real physical camera hardware. Existing camera/OCR code was preserved.
- No database migration was required. Existing unrelated working-tree changes were preserved.

## Changed implementation areas and rollback

Frontend: Explore directory, Accounts, Products split into Cards/Bills/Savings, Insights split into Goals/Statements/Calculators, Support/Knowledge, shared primitives and scoped Explore styles. Backend: owner-scoped goal PUT, optional ticket status filter, catalog-aware simulated beneficiary lookup/save; route matrix and regression tests updated. API notes appended in `docs/release/API_SPEC.md`.

To roll back, revert only these Explore-specific hunks and the new focused component files, rebuild the frontend and restart the same existing launcher. Do not reset the entire working tree: it contains unrelated auth, assistant, QR and reporting work. Persisted records are compatible with the prior schema and should not be deleted.
