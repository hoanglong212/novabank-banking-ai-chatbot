# Banking core foundation — evidence, 31 October 2026

Status: implemented and locally verified for this increment. **The PDF's M1, M2 and full 26-week roadmap remain incomplete. Independent review is pending.**

The user chose to keep the current stack and has no separate 25-function scope, nine-step Alice–Bob script or actual deadline yet. See [plan alignment](PLAN_ALIGNMENT_VI.md) and [business rules](BUSINESS_RULES_VI.md).

## Acceptance → evidence

| Acceptance | Evidence |
| --- | --- |
| Preserve existing balances and history | Legacy migration tests; migration on a SQLite backup of the actual local DB preserved every existing row/column in conversations, messages, tool_events, tickets, accounts, transactions and transfers |
| Balanced, immutable journal | `test_ledger.py`: opening counterentries, no update/delete/replace, no rebase on restart, drift and unbalanced-journal reporting |
| Debit/credit atomicity | Fault trigger during positive journal insert: original balances and transaction count unchanged, no journal/receipt/success audit, separate failure reason |
| Concurrency | Two simultaneous 6m transfers against 10m: one success, one insufficient-funds rejection; same-key confirmations return equal receipts; five concurrent wrong OTPs spend only three attempts |
| Safe retry | Original receipt returned after a later payment changes the balance; conflicting key rejected; keys scoped by owner; bad OTP does not consume key |
| Validation at confirm | Frozen/closed sender/recipient, draft expiry, OTP expiry/action binding and Vietnam-day limit tests |
| Frontend compatibility | Legacy and 32-character draft IDs show review action; API client sends stable key after simulated lost response; production TypeScript/Vite build |
| Real HTTP integration | Isolated local Uvicorn mock instance: compiled assets, readiness/login, Alice→Bob 2m, identical retry receipt, ownership denial, AI draft→OTP confirm, final ledger total 0 |

## Commands actually run

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Final outcome: **136 passed in 33.47s**, versus baseline 94. Tests use temporary SQLite databases; external LLM/bank calls are mocked where needed. Targeted test cycles were observed failing before implementation and passing afterward.

From `frontend/`:

```powershell
npm run test:components
npm run build
```

Final outcome: **11 check groups passed**, TypeScript and Vite build passed (1,601 modules). This runner uses rendered real components and a network-boundary client test; it is not a browser E2E suite.

From root, after real HTTP smoke on port 8091 with `LLM_PROVIDER=mock`, `GATEWAY_MODE=local` and a separate `DB_PATH`:

```powershell
.\backend\.venv\Scripts\python.exe scripts/reconcile.py --db .local/plan-review/live-smoke.sqlite3
git diff --check
```

Reconciliation exit 0: `balanced=true`, `ledger_total_vnd=0`, no mismatches or unbalanced journals. The live smoke server was stopped after checks. Local evidence and migration copy are under ignored `.local/plan-review/`; no test used the original DB for writes.

No `engineering.json`, configured lint/security/coverage gate, Playwright suite or CI run was present for this increment. These are **not configured/not run**, not passing. No real Ollama evaluation, deployment, full research experiment or browser click-through was performed.

## Changes

- `backend/app/ledger.py`: migration, append-only schema, opening ledger, reconciliation.
- `backend/app/posting.py`: shared atomic posting, cache-vs-ledger check, history and audit.
- `backend/app/transfers.py`: serialized confirmation/OTP, draft TTL, idempotent receipt, daily limit by Vietnam day.
- `backend/app/database.py`, `main.py`, `schemas.py`: migration startup, compatible API header/CORS and strict integer money.
- `frontend/src/api.ts`, `types.ts`, `components/transfer/TransferSheet.tsx`: stable confirmation key, immediate submission lock, readable error states.
- `frontend/src/components/chat/MessageThread.tsx`: fixed pre-existing backspace characters in draft-ID regex and supported full UUID references.
- New regression tests, `scripts/reconcile.py`, plan/alignment/rules docs; README and architecture/security notes updated.

The six pre-existing modified UI files (Activity, NavBar, Home and three stylesheets) were preserved. Work is on `feat/banking-core-foundation`; no commit, push or tag was created.

## Review and decisions

Self-review by the implementing assistant against the plan and cross-file contracts. No independent reviewer was dispatched or claimed. Review found and fixed immutable-row REPLACE bypasses, cache drift acceptance and the draft-button regex issue, with failing regression tests before fixes.

Decisions: retain current seed balances, fee 0, amount limits and English UI; adapt concurrency to SQLite; import current balances once rather than invent historical ledger; keep the legacy no-key API response. Full-length UUID references reduce collision risk and retain old eight-character chat links. Consequence: this is an explicitly documented local adaptation, not exact conformance to the PostgreSQL reference design.

Deferred limitations are in [business rules](BUSINESS_RULES_VI.md); next work is M1 identity/session/MFA/RBAC, then the remaining M2 product features and acceptance script. Do not tag a full milestone based on this increment alone.

## Rollback / operation

Stop the app before backup or rollback. Back up the SQLite DB before first running the new backend; an SQLite backup API copy is preferable while any connection may exist. Startup applies additive version 1 once, preserving pre-migration data. Do not run old write code against an upgraded ledger: it can change balances without journal entries. To roll back, restore both the pre-upgrade code and matching DB backup together. If new transfers have occurred, preserve that upgraded DB for reconciliation before any restoration. No automatic downgrade/reset is provided.
