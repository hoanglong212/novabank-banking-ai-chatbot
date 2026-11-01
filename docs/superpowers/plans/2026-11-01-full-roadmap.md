# Full roadmap implementation — 2026-11-01

Goal: finish the remaining local implementation in the user's 23-page Banking Web App + AI Agent plan. User explicitly requested all remaining work. Execute inline; no additional approval for ordinary implementation/testing, no automatic dependency installation, services, commits, pushes or deployment.

Architecture: preserve React/Vite/TypeScript and FastAPI/SQLite. Versioned additive migrations preserve user data. Integer VND and one balanced posting primitive serve every product. Customer confirmation stays in banking API. Agent runs in a separate HTTP service with delegated read/prepare permissions. Research uses isolated data only.

Spec: the supplied PDF; `BUILD_SCOPE_VI.md`, `BUSINESS_RULES_VI.md`, existing milestone plans. P2 items remain optional. Local completion and external release evidence are reported separately.

Scope confirmed by user on 2026-11-01: local only. VPS/domain, public HTTPS, container deployment and remote release are not acceptance requirements for this delivery. Existing dependency advisories and lack of independent review remain disclosed limitations.

Global constraints: preserve all existing uncommitted work; never reset the user's database; tests use temporary databases. No real bank/payment network. Keep English UI and existing tokens. Do not count mock-model tests as measured security research. Do not claim external CI/deployment/review/video evidence without executing it.

Review focus: cross-user isolation, session revocation, OTP purpose binding/replay/attempt exhaustion, concurrent and idempotent posting, immutable history, delegated authorization, untrusted data boundaries, no secret leakage, functional responsive UI.

## Execution ledger

- [x] M1 account/profile: `banking_schema.py`, `customer_services.py`, `routes_customer.py`; pending email/phone/password changes bound to session + OTP, account nickname/detail, owner-scoped verified beneficiaries. Test successful changes, expiry/replay, wrong-owner and lockout before implementation.
- [x] M2 payments: extend `posting.py` with shared journal primitive; fees/limits, asynchronous interbank settlement/reversal, reconciliation worker and internal QR. Test concurrency, rollback, idempotency and mixed reconciliation.
- [x] M3 products: `products.py`, routes and Explore screens for cards/bills/savings/goals/calculators, categorization/budgets, monthly analytics and PDF/CSV statements. Test every financial path and ownership.
- [x] M3 support/admin: manual tickets/replies/attachments, assignment, user/account lifecycle, settings, knowledge approval and admin summaries. Enforce role permissions at API.
- [x] M4 agent: separate `agent_service`, short delegated grants and tool API; source/trust metadata RAG using locally available embeddings; approvals, SSE events, persisted runs/tool traces with limits.
- [x] M5 lab: sandbox provisioning, >=30 scenarios across seven vectors, >=60 legitimate tasks, naive/baseline/defended profiles, 10 defenses, deterministic evaluator and ablations; run actual two-model/five-repeat experiments and preserve raw results.
- [x] Frontend integration: preserve main navigation, group products in Explore, staff tools in Operations, research views separated. Full loading/empty/error/pending/confirmation states and keyboard/mobile checks.
- [x] M6 local artifacts: 12 documents, OpenAPI, security PDF, 10 HTML slides, 5m11s recorded demo, CI/Compose/Caddy configuration, encrypted backup + verified restore, security headers and seeded demo.
- M6 external release: outside the user-confirmed local-only scope; not executed or marked as passed. Dependency advisory remediation and independent review remain documented limitations.
- [x] Verification: configured backend/component/build/E2E commands, financial coverage if tooling available, migration on a copy, ledger reconciliation, isolated real-model runs, responsive screenshots and self-review. Record exact outcomes and remaining limitations.

## UI direction decision

1. Expose each product in global navigation: direct access but overcrowds mobile.
2. Group daily products in Explore and staff workflows in Operations: selected; retains familiar shell and makes new workflows discoverable without increasing primary navigation density.
3. Separate customer, staff and research applications: clear boundaries but duplicates shell and complicates this demo's deployment.

Reuse current spacing, colors, typography and accessible Sheet/form components. New screens prioritize task actions, ledger-backed history and visible confirmation state over decorative dashboards. Maximum three visual QA assessments for this implementation cycle.

## Verification commands

`backend/.venv/Scripts/python.exe -m pytest -q` (cwd backend)

`npm run test:components`, `npm run build`, `npm run test:e2e` (cwd frontend)

Targeted tests run red before relevant implementation, then green; full suites at integration boundaries. Use temporary files under `.local/full-roadmap` for evidence. Missing tools are reported, never silently installed.

## Final local evidence

See [STATUS](../../release/STATUS.md): 224 backend tests, 93.27% financial line coverage, 15 component groups, 12 E2E, 44 responsive captures, 1790 model observations, copy migration and restore. M6 local artifacts complete; external release is outside the confirmed scope. HTML slides used because integrated PPTX runtime unavailable. No original DB mutation or automatic installs.
