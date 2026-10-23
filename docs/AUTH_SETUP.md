# Authentication setup — 23 October 2026

## Local development

From the repository root:

```powershell
rtk proxy .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
rtk proxy .\backend\.venv\Scripts\python.exe scripts/init-demo-auth.py
```

The initializer adds missing JWT_SECRET and DEMO_ALICE_PASSWORD / DEMO_BOB_PASSWORD to ignored backend/.env. Values are generated randomly and not printed. Keep that file private. Accounts are seeded at backend startup with Argon2id hashes; changing seed passwords later does NOT reset existing accounts. There is no public registration/password-reset endpoint.

For HTTP loopback development set AUTH_COOKIE_SECURE=false explicitly. The initializer sets it only when that setting is absent; if .env was copied from the template with `true`, change it to false for HTTP loopback. For HTTPS demo use true. Secure cookies on plain HTTP can prevent login from persisting. APP_ORIGINS must list exact UI origins, separated by commas (scheme, host and port; no trailing slash). Examples: http://127.0.0.1:5173 and http://127.0.0.1:8080. Same-origin Vite proxy already exists. Do not expose the loopback development configuration publicly.

Restart backend after installing/configuring. Build frontend with `npm run build` in frontend for the single-port launcher, or run `npm run dev` with backend on :8000. Sign in as `alice` or `bob` with the corresponding password from the local .env file. Reload restores the cookie session. Sign out before changing users. The old identity selector and static bearer tokens no longer work.

## Session behavior

- Default absolute TTL: 3600 seconds (SESSION_TTL_SECONDS); bounded to 60–86400.
- No refresh or sliding expiration. Expiration requires sign-in again.
- JWT: HS256 with issuer/audience, required exp/iat/sub/jti. Secret must be at least 32 bytes.
- Server verifies active user, session owner, expiry and revocation on each request.
- Cookies: HttpOnly, SameSite=Lax, Secure by default, path=/.
- Login requires an allowlisted Origin. Writes require Origin and session-bound X-CSRF-Token.
- Logout revokes the session and clears the cookie. Replayed old cookies fail.
- Login throttling: 5 attempts per username and 30 per direct client IP per five minutes (successful attempts also count). It is a demo policy, not distributed abuse protection. Forwarded IP headers are not trusted automatically.
- Auth/API responses use Cache-Control: no-store.

The browser never reads the JWT. It obtains a CSRF token from login/session responses and keeps that token in memory. Cookies authenticate requests; CSRF tokens alone cannot authenticate.

## Verification

`scripts/verify-auth-live.py` creates a temporary DB/server, uses local seed configuration, checks assets/API/login/isolation, then stops its own process and removes its temporary DB. It does not use or change the existing demo DB.

`npm run test:identity` uses the existing isolated Edge CDP harness at :9224. The wrapper starts its own backend and Vite on free loopback ports with a temporary database and an exact matching Origin allowlist. It reads local seed credentials without printing them, tests sign-in/reload/user isolation, preview/reload/confirm and recipient balance/history, then stops its own servers and removes the temporary database. Browser verification is separate from backend TestClient coverage.

## Scope and rollback

This is an authentication foundation, not a claim of production banking security. Accounts and balances remain simulated, remote security gateway integration remains pending. PII history/trace filtering and LangGraph integration are not implemented yet.

To roll back code, selectively revert this task's source changes after reviewing your working tree; do not discard unrelated files. Back up the demo DB first. New auth tables are additive and can remain unused; no destructive schema rollback is necessary. Remove local seed environment settings only if intentionally retiring those credentials. Reverting to the old app re-enables insecure demo bearer authentication and is suitable only for a private local demo.
