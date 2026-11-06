# NovaBank Banking Web App + AI Agent

A local banking simulation and prompt-injection research project. React 19/Vite/TypeScript/Tailwind, FastAPI/SQLite, and a separate HTTP agent using local Ollama. All accounts and money are fictional.

**Current handoff:** [implementation and verification status](docs/release/STATUS.md), [12-document dossier](docs/release/README.md), [25 use cases](docs/release/SRS.md), [security report PDF](docs/release/Security-Evaluation.pdf), [demo video](docs/release/media/NovaBank-demo.mp4), [defense slides](docs/release/Defense-Slides.html).

Local implementation and research have been verified. The user confirmed local-only delivery on 2026-11-01: public HTTPS, VPS/domain, Docker deployment and remote release are outside the accepted scope. Dependency advisories and the absence of independent review remain documented limitations. No v1.0 release is claimed.

**Latest acceptance fixes:** the 10 requested cases and 4 ratified specification decisions are verified: 271 pytest tests, 17 component groups and 15 E2E tests pass; reconciliation is balanced. See the [before/after report and exact commands](docs/release/acceptance-fixes/REPORT_VI.md). AI-14 / PI-05 / PI-06 are deferred by request. The [original 121-case audit](docs/release/acceptance-audit/REPORT_VI.md) remains historical evidence; this fixes report does not claim every research criterion is complete. The existing demo backend was not restarted or written to during this work.

## Run locally

For the local instance started on 2026-11-01, use [its login, MFA and restart instructions](docs/release/LOCAL_RUN.md). It uses a separate seeded database under `.local/local-deploy`.

With the repository's existing dependencies and local Ollama models:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Mode ollama
```

Open http://127.0.0.1:8080. The launcher builds the frontend and starts the bank plus isolated agent (:8093). Ctrl+C stops both. `-Mode mock` uses explicitly labeled deterministic responses without a model. The command does not install dependencies or pull models. See [deployment and configuration](docs/release/DEPLOYMENT.md).

Demo logins: `alice / Alice@2026`, `bob / Bob@2026`, `charlie / Charlie@2026`; staff `support / Support@2026`, `  / Operations@2026`, `auditor / Auditor@2026`, `admin / Admin@2026`. Every login requires email MFA or configured TOTP. Retrieve simulated email through `scripts/dev-outbox.py --help`, using the same DB as the server. Never paste OTPs into assistant chat.

Public demo credentials require a restricted review environment. The supplied Compose/Caddy configuration includes an access gateway. Do not use real banking credentials or PII.

## Capabilities

- MFA, rotating refresh sessions, recovery, profile changes with current password and OTP.
- Double-entry transfers, locked fees, daily limits, idempotency, interbank pending/reversal, internal signed QR, receipts and alerts.
- Debit/credit simulation, bills, term savings, goals/calculators, monthly spending/budgets and PDF/CSV statements.
- Customer support with attachments/replies, role-based operations/admin, approved knowledge library.
- Isolated agent with short delegated grants, RAG citations, approval cards, streamed progress and persisted tool traces. No agent confirm authority.
- Resettable research sandbox, 35 attack scenarios/7 vectors, 100 legitimate tasks, two models, naive/baseline/defended profiles, D1-D10 ablations and results dashboard.

QR is NovaBank-only, not NAPAS/VietQR. Legacy endpoint names remain for compatibility, but no external bank-list or QR service is called. Email/SMS/KYC are simulated. The Group 10 external gateway remains an adapter contract, not a verified integration.

## Verification

```powershell
.\backend\.venv\Scripts\python.exe scripts/financial-coverage.py
cd frontend
npm run test:components
npm run test:e2e
```

Latest results: 224 backend tests; financial line coverage 93.27%; 15 component groups; 12 browser E2E tests; build passes. E2E deterministic legacy-agent checks are separate from the real two-process/model acceptance in `scripts/check-agent-service.py` and `frontend/scripts/release-browser.mjs`.

Measured research: 1,790 observations, zero execution errors, balanced sandbox journals. Defended utility Qwen99% / Llama90%, ASR0 within this controlled corpus. Read [method and limitations](docs/release/PI_RESULTS.md) before interpreting those numbers.

## Data, backups and artifacts

`scripts/seed-demo.py --out <NEW.sqlite3>` creates five synthetic customers and six months of activity without overwriting an existing target. The normal app migrates existing databases additively. `scripts/check-migrations.py` tests copies; the original DB files were not changed during implementation.

`scripts/backup.py` creates encrypted consistent snapshots and restores only to new paths, including per-DB MFA keys. Keep the backup encryption key separately. [Operator guide](docs/release/ADMIN_GUIDE.md) explains settings, reconciliation and research.

Historic milestones remain in `docs/`; their test counts and partial scope are historical. Use `docs/release/STATUS.md` as the current record. Pre-existing uncommitted work has been preserved; no commit/push/tag or public deployment was performed.
