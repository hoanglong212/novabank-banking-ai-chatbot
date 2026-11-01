# M1 sessions, MFA and login history implementation plan

> Execute inline with msi-aef-executing-plans and meaningful TDD. Preserve existing changes; no automatic commits, pushes, installs or subagents.

**Goal:** Password login requires a second factor; users can manage sessions, inspect sign-in history and configure TOTP, with persisted 15-minute lockout.

**Spec:** User selected this M1 scope from PDF `(3)`, sections 6/15. Existing register/verify/reset and banking behavior must remain intact. Profile editing/password change with OTP are separate next work.

**Architecture:** SQLite migration v4 adds session/refresh lineage, login attempts/lockouts, action-bound MFA challenges and encrypted TOTP settings. Server checks every JWT's session, credential version, idle and absolute lifetime. The existing local outbox delivers simulated email OTPs. Auth UI gains an OTP step; Profile embeds a Security Center. No service/stack change.

## Decisions (implementation choices within the selected scope)

- All users, including demo staff, need MFA. Default is email OTP through local outbox; TOTP becomes the default after explicit setup. Email remains the recovery fallback, with the demo's documented local-mail limitation.
- TOTP: RFC 6238 SHA-1, six digits, 30-second step, ±1 step tolerance; global last-used step prevents reuse. Setup expires after five minutes and needs current password and a successful TOTP confirmation. Disable requires password plus a separate email challenge tied to the current session. Factor changes revoke other sessions and pending login challenges.
- Existing `cryptography` 50.0.2 is already installed; declare it directly in requirements, without installing/upgrading packages. Fernet encrypts TOTP seeds using `MFA_ENCRYPTION_KEY` when supplied, otherwise a randomly generated per-DB `.mfa.key` file (ignored, beside the DB). Preserve/back up key with DB; do not log it or store it in DB. Manual authenticator key entry avoids a new QR dependency.
- Access JWT: five minutes, required `sid` and credential version. Refresh: opaque 256-bit token, hashes only in SQLite; single-use rotation. Reuse of a spent refresh token revokes its session family. No grace replay cache; a lost refresh response requires sign-in. Existing pre-v4 JWTs require reauthentication.
- Session idle limit: five minutes; absolute limit: eight hours. Background polling and refresh do not count as activity. A throttled browser interaction endpoint updates activity; backend enforces deadlines independently. Local browser timeout handles sleep/visibility changes. No browser input is treated as proof of a human.
- Keep per-tab bearer/sessionStorage model, including refresh credentials, to preserve multi-customer demo behavior. No ambient cookies or CSRF-bearing cookie auth is introduced. XSS/browser storage risk remains documented; production HttpOnly cookie design is future work.
- Five failures (password/MFA combined per normalized login) in a 15-minute window lock authentication for 15 minutes. Counters and history persist in SQLite; successful full MFA clears failures. Unknown usernames receive equivalent password/lockout behavior. Expiry checks happen after acquiring SQLite's write lock.
- Login challenge lifetime five minutes; email OTP two minutes, five attempts, resend cooldown 30 seconds and at most three resends without extending challenge expiry or resetting attempts. Bind login challenge to user/credential version and action; disable-TOTP challenge also binds session. HMAC OTP with server key, no raw OTP in API/audit.
- History records timestamp, bounded/sanitized user agent, connection peer IP, result and factor. Never trust X-Forwarded-For. New IP+UA after a previous successful sign-in creates a local notice. History and sessions are owner-scoped and bounded/paged. Fingerprint is a heuristic, not a trusted device credential.

## Alternatives considered

1. Selected: extend current auth shell + Security Center inside Profile. Keeps existing navigation/mobile layout and exposes controls where users expect them.
2. Separate identity provider/service: adds infrastructure outside authorized stack.
3. Optional MFA only and stateless JWT logout: leaves the requested login/revocation boundaries incomplete.

## Review focus

1. Correct password or pending MFA must never create an authenticated session; cross-purpose/replayed OTPs fail, including concurrent consumption.
2. Revoked/idle/absolute-expired sessions and reset credentials cannot be revived by refresh, polling, a stale browser tab or legacy JWTs.
3. Refresh rotation/reuse and lockout updates must remain atomic under concurrent requests and after restart.
4. TOTP setup/disable secrets must not leak to history, outbox metadata, URLs, logs or other users; pending setups cannot override active factors.
5. Refresh and activity handling must avoid request storms, polling keeping idle sessions alive, stale credential responses restoring a logged-out user, or changing the signed-in identity across tabs.

## Work ledger

- [x] Backup current DB; API/RFC-vector tests from the existing increment verified in the 198-test suite. Original red evidence for those prior backend changes is not claimed by the continuation.
- [x] Existing v4 migration, crypto/login/MFA/session services, reset revocation and backend helpers verified. Original frontend mismatch was reproduced before repair.
- [x] Existing outbox CLI selected-message disclosure/scrubbing and new-device tests pass; CLI also packaged for Docker (image not run).
- [x] Implement OTP login, refresh/idle coordination and Profile Security Center; component race tests and browser login helpers updated.
- [x] Browser acceptance for session revoke/history/TOTP/fallback and new-customer receipt: 198 backend tests, 14 component groups, production build and 10 E2E tests passed.
- [x] Self-review, migration on DB copy, reconciliation, mobile/desktop image inspection and documentation completed. Independent review and remote CI remain pending.

Continuation evidence: [m1-sessions-mfa-completion.md](../../m1-sessions-mfa-completion.md). Whole M1 is not marked complete; profile editing and authenticated password change remain separate next work.

Baseline: 185 backend tests, 13 component groups, 7 browser tests passed in previous increment; CI not run remotely. Existing working tree contains all prior uncommitted feature work.

References consulted: [RFC 6238](https://www.rfc-editor.org/rfc/rfc6238), [Fernet](https://cryptography.io/en/latest/fernet/), [OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [refresh token rotation guidance](https://www.rfc-editor.org/rfc/rfc9700). This is a local simulation, not OAuth/production assurance.
