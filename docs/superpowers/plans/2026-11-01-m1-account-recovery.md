# M1 registration, verification and password recovery

> Execute inline with msi-aef-executing-plans and TDD. Preserve all existing work. No automatic commits, pushes, dependency installations or subagents.

**Goal:** A new customer can register, verify through a local development outbox, sign in, and recover a forgotten password without changing any existing financial data.

**Spec:** User selected “Làm tiếp M1: đăng ký, xác minh, khôi phục mật khẩu” after supplying PDF `(2)`, sections 6 and 15. Full MFA, refresh rotation, session management, profile editing and M2 remain separate.

**Architecture:** SQLite migration v3 persists the seven existing principals with their unchanged IDs, roles and password hashes. Purpose-bound random tokens are stored hashed; actionable messages live only in a local SQLite development outbox read with an explicit CLI. Email verification atomically opens one zero-balance customer account and its ledger mapping. Reset increments a credential version checked on every JWT request.

**Stack:** Existing React/Vite/FastAPI/SQLite and Python standard library. No new dependency or external email delivery.

## Decisions

- User IDs remain immutable normalized usernames (3–32 ASCII letters/digits/underscore, starting with a letter). Display names support Vietnamese. Email is normalized/lowercase with bounded basic format validation; this demo does not deliver actual email.
- New/reset passwords: 15–128 characters, allow spaces/Unicode/paste, no arbitrary composition rules. Existing demo passwords remain valid. Retain PBKDF2-HMAC-SHA256 compatibility, use 600,000 iterations for newly stored hashes.
- Verification token: 256-bit randomness, 24-hour TTL (implementation choice). Reset token: same randomness, 15-minute TTL specified by the PDF. Resend invalidates the old token. Token consumption and changes share `BEGIN IMMEDIATE`.
- Public registration/forgot/resend responses do not disclose whether username/email exists. Do not overwrite an existing pending account during repeated registration. Persistent request limits: 20 requests per source IP/action/15 minutes; delivery at most 5/email/purpose/hour, silently suppress excess deliveries. Client IP is the connection peer, not an untrusted forwarded header.
- New users are always customers. Public schemas reject extra role/account/balance fields. Outbox has no HTTP endpoint, even for staff. CLI displays metadata by default; explicit `--id` reveals a development message/action URL. Fragment URLs keep tokens out of server access logs; frontend removes the fragment token after reading it.
- No auto-login after verification/reset. A successful reset invalidates all reset tokens and all prior JWTs via `auth_version`; migration accepts old demo JWTs as version 0 until a reset. Active sessions/refresh/idle timeout are not claimed complete.
- Security references: OWASP Forgot Password and Authentication cheat sheets (consulted 1 November). Generic response/timing work reduces enumeration signals; this is not a proof of constant-time HTTP handling or production readiness.

## Review focus

1. Duplicate/concurrent registration or verification must not create duplicate accounts, alter an existing password, or create money.
2. Wrong-purpose, expired, invalidated and replayed tokens must have no effect; concurrent reset consumption must succeed once only.
3. Existing identities, messages, transfers, balances and ledger must remain intact across repeated startup and schema migration.
4. Password reset must reject old JWTs immediately and retain the new hash after restart; user-supplied role claims never grant staff permissions.
5. Outbox/token/password material must not appear in public responses, audit metadata or application request URLs.

## Tasks

- [x] Backup current DB via SQLite backup; write failing integration tests for register/verify/recovery/migration/atomicity/limits/isolation.
- [x] Implement `identity_schema.py`, request schemas and `identity.py`; adapt `auth.py` to persisted users and credential versions. Add `/api/auth/register`, `/verify-email`, `/resend-verification`, `/forgot-password`, `/reset-password` routes. Run focused and full backend suites.
- [x] Add read-only `scripts/dev-outbox.py` with explicit DB path and safe loopback link origin; execute CLI regression tests.
- [x] Extend existing authentication UI with Register, Verify email, Forgot password and Reset password forms, visible success/error/loading states and links. Keep the current login layout/design tokens and demo entry points. Update component checks.
- [x] Extend Playwright with real-backend register → outbox → verify → login → forgot → reset → login and old-session rejection. Outbox test helper reads only the disposable test DB, with no test HTTP endpoint. Build, run E2E and inspect mobile/desktop screenshots.
- [x] Review diffs; migrate a copy of the real DB and verify old rows/hash unchanged; update README, business rules, checklist and completion evidence. Independent review remains pending; no release or full M1 completion claim.

## UI choices

1. Selected: reuse current authentication shell and switch forms; verification/reset links open the right form with a fragment token. Preserves branding and avoids another routing dependency.
2. Separate full-screen shell for each form: unnecessary duplication.
3. Put registration/recovery inside login modal sheets: cramped on mobile, harder to open external verification links.

## Progress

Baseline from previous increment: 158 backend tests, 12 component groups, 3 browser tests, build and financial reconciliation passed. GitHub has no workflow run for the local feature branch; this user-selected increment does not include publishing.

Implemented locally; see [acceptance evidence and limitations](../../m1-account-recovery-completion.md). Review found an expiry race when waiting for SQLite's write lock; a failing regression test reproduced it and verification/reset now read the clock after acquiring that lock.
