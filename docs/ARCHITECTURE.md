# Architecture and data flow

```text
React + TypeScript UI
  -> FastAPI (authenticated demo principal from bearer token)
     -> SQLite (conversation ownership, messages, tool decisions, tickets)
     -> Agent (mock or Ollama /api/chat)
        -> Proposed tool name + validated arguments
           -> ToolDispatcher -> PolicyGateway.authorize(...) -> ALLOW/DENY audit
              -> On ALLOW only: simulated tool executor
              -> Tool result to Agent -> final assistant message
```

The `mock` agent chooses actions deterministically for offline demos; **it is not a generative AI**. In both modes, `bind_request` selects an operation and binds resource IDs to user input. With `LLM_PROVIDER=ollama`, one model request proposes a native tool call constrained to that operation. The application validates the proposal, audits mismatched tools, and executes at most one user-bound operation through the dispatcher. Missing or malformed proposals use the application fallback. Tool observations are rendered by the application, not passed back to the model. Up to the last 24 user/assistant messages are sent as context while full history remains in SQLite. `response_source` distinguishes native, rebound, fallback and template responses.

Development uses Vite on port 5173 and FastAPI on 8000. The demo launcher and Docker image set `FRONTEND_DIST` to the compiled UI directory so FastAPI serves both UI and API on one port. Static serving is registered after API routes and never exposes backend source or `.env`. `/api/health` is a liveness/configuration check; `/api/ready` checks that the configured Ollama model is installed and reachable (or reports ready immediately in mock mode). Readiness does not generate text, measure model quality, validate GPU capacity, or probe the remote policy gateway.

A dedicated `PolicyGateway` class decides, but does not execute tools. Local mode performs allowlist, schema, and ownership checks. Remote mode performs the same local checks and then sends an adapter request to a hypothetical `/authorize` endpoint; it FAILS CLOSED if remote gateway fails. The proposed API contract is NOT guaranteed to match Group 10's actual runtime security gateway.

Audit records ALLOW and DENY and whether execution happened. `demo/tool-check` evaluates policy but never executes, even for ALLOW. Frontend displays the latest events to help demonstrate decisions. No payment API, real customer records, real OTP, credential-handling or bank integration are implemented.

## Banking core continuation (31 October 2026)

The authenticated API owns `transfers.prepare/issue_otp/confirm`. Only prepare is exposed to the agent dispatcher. `confirm` obtains a SQLite `BEGIN IMMEDIATE` write lock before reading the current OTP, draft state and receipt key, then invokes `posting.post_transfer` in the same transaction. Financial changes, ledger rows, customer history, success audit and keyed receipt commit together. Wrong-OTP counters are also serialized; storage/financial failures roll back and may be recorded separately as FAILED.

`ledger.initialize_ledger` is an additive versioned migration. It imports current account balances as opening journals against internal equity; it does not reconstruct old history. Internal ledger accounts are separate from customer `accounts`, so clearing/equity never appear in `/api/me`. Ledger/account mappings, banking audit and receipts are append-only. `ledger.reconcile` checks every journal, the global zero sum and customer cached balances in one snapshot; `scripts/reconcile.py` exposes this as an explicit local command.

`Idempotency-Key` is optional for old API clients and mandatory in the updated frontend helper. A successful key is scoped by authenticated owner and transfer ID, returns the persisted original receipt, and contains no OTP. Invalid OTP attempts do not reserve a key. The UI keeps one key per mounted transfer flow and prevents a second submit before the first render update.

This keeps the existing single-process agent/dispatcher design. A separate agent service with delegated read/prepare-only tokens, RAG, profile switches and research run tables is still planned; this implementation does not claim that service boundary. See [alignment](PLAN_ALIGNMENT_VI.md) and [business rules](BUSINESS_RULES_VI.md).

## Transaction experience (1 November 2026)

Schema v2 adds immutable `transaction_details` keyed by customer transaction and `notifications` unique per owner/transaction. Posting writes both parties' counterparty/balance snapshots and money-in/out notifications inside the existing confirmation transaction. Legacy payer snapshots can be imported from v1 success audit; unknown historical balances remain null. No historical ledger journal is rebased.

`dependencies.py` resolves the authenticated principal and server-owned permissions. Customer history/detail/PDF queries are owner-scoped; notification reads/updates are owner-scoped for every role. Operations/auditor/admin can use bounded `/api/admin/transactions` and correlated transfer audit endpoints. Support has no global financial-read permission. Staff cannot reach customer transfer/chat tools. Role metadata is returned by login/me for navigation, but enforcement never depends on frontend visibility.

`banking_queries.py` uses parameterized filters, escaped literal search, bounded pagination and a read transaction for consistent totals/items. ReportLab renders completed receipts from recorded data and embeds Noto Sans. React reuses native dialog sheets for details; Activity filters request server pages, Alerts polls every 15 seconds only while visible, and Operations is a separate staff view. `scripts/run-e2e-server.py` provides a private process-only seed override for acceptance; no reset or test route is exposed by the application.
# Persisted identity extension (1 November 2026)

Migration v3 adds `users`, `identity_tokens`, `dev_outbox`, `identity_limits` and `identity_audit` without rewriting financial/chat tables. Existing seed IDs and password hashes are inserted once; resets survive startup. `identity.py` owns transactional verification/recovery and zero-balance account opening. `auth.py` looks up active principals and credential versions in SQLite on authentication; JWT role claims never grant permissions. `routes_identity.py` exposes bounded register/verify/resend/forgot/reset requests. Sensitive validation responses omit raw input.

React `AuthFlow` reuses `AuthShell` and the existing login. Verification/reset fragment links are parsed into memory and removed from the URL; no token is saved in browser storage. Opening an action link leaves the current tab's signed-in session. Successful actions require a fresh login. `scripts/dev-outbox.py` reads explicitly selected local databases with `mode=ro`; there is no inbox HTTP route or outbound delivery service.

See [account lifecycle rules](ACCOUNT_RECOVERY_VI.md). Production mail remains outside this increment; the following continuation adds MFA and session management.

## MFA and sessions continuation (1 November 2026)

Migration v4 adds `user_sessions`, hashed refresh-token lineage, persisted login lockouts/history, purpose-bound MFA challenges and encrypted authenticator settings. `routes_sessions.py` starts login with HTTP 202; only successful `/mfa/verify` creates a session. `sessions.py`, `mfa.py` and `session_security.py` serialize mutations under the existing SQLite transaction helper. `auth.authenticate` checks both the signed JWT and current server-owned session/credential version. TOTP encryption keys are outside SQLite; backups must include the per-DB key or configured environment key.

React's `sessionStore.ts` holds one session per tab, deduplicates refresh, binds responses to the current session and preserves a stable user reference during token rotation. Authenticated API requests resolve current credentials rather than retaining an old bearer token; one HTTP 401 may trigger rotation/retry. Lost refresh replies require sign-in rather than replaying a spent token. Background requests never extend idle lifetime. The session hook checks wall-clock expiry and sends throttled activity only for visible-page input.

`MfaSignIn` handles email/authenticator codes and email fallback without persisting challenges. `Profile` embeds `SecurityCenter` and `AuthenticatorSettings` for revocation/history and factor setup/disable. All actions call the real authorization-checked backend. The outbox CLI is packaged in Docker for local operator access; no inbox route or MFA bypass was added. See [operation and limitations](SESSIONS_MFA_VI.md).
