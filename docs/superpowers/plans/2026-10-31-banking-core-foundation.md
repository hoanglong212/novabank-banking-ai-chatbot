# Banking Core Foundation Implementation Plan

> **For agentic workers:** Use `msi-aef-executing-plans` inline, task by task, with the local ledger below. No automatic commits, pushes, tags, installs or subagent dispatch.

**Goal:** Add a verifiable ledger and safe confirmation/retry semantics to the existing simulated transfer flow without resetting existing user data.

**Architecture:** SQLite additive, versioned migration creates an immutable signed ledger and opening balances. A single posting service writes balances, journal, transaction history, audit and idempotent receipt in one transaction; confirmation validates OTP and mutable account state under the same write lock. A local reconciliation command checks a consistent database snapshot.

**Tech Stack:** Existing FastAPI/Pydantic/sqlite3/pytest and React 19/Vite/TypeScript/npm; no new dependencies.

**Spec:** PDF sections 7, 8, 12, 13, adapted by user decision recorded in [PLAN_ALIGNMENT_VI.md](../../PLAN_ALIGNMENT_VI.md).

## Global constraints

- Preserve existing frontend work, account balances and historical messages/transactions.
- Integer VND only; 1,000–100,000,000 per transfer, 200,000,000/day, existing fee 0. All transfers require their own OTP (2 minutes, 3 attempts); draft lifetime 5 minutes.
- Daily limit uses Vietnam calendar day (UTC+7); persisted timestamps remain UTC.
- `PENDING_OTP` remains the wire status for compatibility. Completed confirmation without a key still returns `ALREADY_PROCESSED`; matching successful idempotency retry returns the original receipt.
- SQLite `BEGIN IMMEDIATE` is the local implementation, not row locking or a PostgreSQL benchmark.
- Old history is retained. Opening journal captures current balances once, not reconstructed historical accounting.

## Review focus

- Migration/restart must not reset a changed balance, duplicate openings or silently repair drift.
- Two concurrent confirmations must share the OTP attempt budget and never overspend or post twice.
- Idempotency keys are scoped by authenticated user, cannot be reused for another transfer, contain no OTP, and return the original receipt even after later balance changes.
- Frozen/closed accounts, expired drafts and daily limits must be rechecked at confirm; resending OTP cannot extend a draft.
- Failure after the debit or journal write must roll back all financial effects; the failed transfer may be recorded separately with a safe reason.

## Task 1 — Ledger and migration

Files: `backend/app/ledger.py`, `backend/app/database.py`, `backend/tests/test_ledger.py`.

Interfaces: `initialize_ledger(conn, stamp)` runs in the initializer transaction; `reconcile(db) -> dict` records a consistent report. Customer `accounts` stay separate from internal ledger accounts (opening equity, interbank clearing).

- [x] Write failing tests for opening sums/current balance preservation, restart idempotence, immutable ledger, discrepancy detection.
- [x] Add versioned migration; ledger entries use signed integer VND, journal IDs and account FKs. Database triggers prevent update/delete. Add account state and failure reason fields additively.
- [x] Run `python -m pytest tests/test_ledger.py -q`, then expand tests through actual transfers in Task 2.

## Task 2 — Atomic posting and confirmation

Files: `backend/app/posting.py`, `backend/app/transfers.py`, `backend/app/schemas.py`, `backend/app/main.py`, `backend/tests/test_banking_core.py`.

Interfaces: `post_transfer(conn, transfer, stamp) -> receipt`; `confirm(db, user, transfer_id, otp, idempotency_key=None) -> dict`. Dispatcher keeps using `prepare` and never gets confirmation capability.

- [x] Write failing tests: balanced internal/interbank postings, rollback via SQLite fault trigger, 2 simultaneous 6m transfers from 10m, same draft/key concurrent retries, same key/different draft conflict, cross-user denial, strict amount input.
- [x] Add draft expiry, Active/Frozen/Closed validation, atomic OTP checks and retry counters, persistent original receipts; allow `Idempotency-Key` in CORS.
- [x] Verify expiry at boundary, resend cannot revive expired draft, invalid OTP does not consume key, recheck daily limit/current account state.
- [x] Run targeted tests and original transfer suite.

## Task 3 — UI retry contract, CLI and documentation

Files: `frontend/src/api.ts`, `frontend/src/components/transfer/TransferSheet.tsx`, `frontend/tests/components.test.tsx`, `scripts/reconcile.py`, `docs/BUSINESS_RULES_VI.md`, README and completion evidence.

- [x] Verify frontend client sends the stable key on retry with a network-boundary test using the existing runner.
- [x] Keep one key per transfer flow and block duplicate submissions immediately; show clear expired/frozen/conflict/storage errors using existing layout.
- [x] Add reconciliation CLI (explicit existing DB path; no initialization/reset); successful check exits 0, imbalance 1, invalid path 2.
- [x] Run all backend tests, frontend build/component checks, CLI clean/drift cases, diff review.
- [x] Record fulfilled and remaining PDF requirements, checks and independent-review limitation.

## Execution ledger

- Baseline: 94 backend tests, frontend build and 9 component groups passed.
- Decision: user approved preserving current stack and implementing missing requirements; no separate plan permission needed.
- Decision: keep existing balances, fee 0, amount limits and English UI. Changes to these product rules require a later explicit specification.
- Decision: this deliverable is the M2 posting foundation, not the entire 26-week roadmap. Remaining milestones stay visible in the alignment document.
- Pre-flight: Task 2 consumes ledger schema from Task 1; Task 3 consumes optional-key confirmation from Task 2. Existing no-key clients retain their response contract.

- Task 1 complete: opening migration/restart/preservation/immutability/reconciliation tests passed; no live database reset.
- Task 2 complete: atomic posting, retry, concurrency, expiry, states and day boundary tested; final backend suite 136 passed.
- Task 3 complete: frontend 11 check groups and build passed; local real HTTP smoke and CLI reconciliation passed; evidence in docs/banking-core-completion-2026-10-31.md.
- Review decision: full UUID transfer IDs require supporting both old and new IDs in MessageThread; regression also found pre-existing backspace characters in its regex, fixed in this increment.
- Review decision: add REPLACE guards because SQLite replacement bypassed ordinary immutability triggers; reject cache/ledger mismatch before posting.
- Final review: self-review by author; independent review pending, no automatic agent dispatch or commit.
