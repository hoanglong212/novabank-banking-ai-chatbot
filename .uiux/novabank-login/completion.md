# Login redesign verification — 2026-11-07

Implemented the selected editorial direction in `frontend/src/components/auth/Login.tsx`, new `LoginShell.tsx` and scoped `frontend/src/styles/login.css`. Design rationale: `decisions.md`.

## Evidence

| Acceptance | Verification |
| --- | --- |
| Compiles using the existing stack | `npm run build` in frontend: PASS (TypeScript + Vite) |
| Existing component contracts | `npm run test:components`: PASS. An initial failure exposed hidden optional navigation links; restored their presence and disabled them only when callback is unavailable. |
| Real identity flow preserved | `npx --no-install playwright test tests/e2e/identity.spec.ts`: 4 passed (31.3s), using repository disposable database/server. Includes registration, verification, MFA sign-in, password recovery/session revocation and responsive recovery forms. |
| Responsive layout and browser runtime | `uiux qa --url http://127.0.0.1:5173 --out .local/login-design/qa-final`: PASS, 375/768/1440 px, no horizontal overflow, unnamed controls or runtime errors. |
| Visual review | Primary agent opened all initial and final mobile/tablet/desktop PNGs plus error-desktop.png. Reduced illustration height after first review to fit the desktop page at 1440x900; removed a decorative arrow that implied an unavailable action. Final layout has no visible clipping/overlap. |
| Login interactions | Local Playwright smoke checks passed at 320/375/768/1024/1440 px: both demo accounts autofill; show/hide password; empty submit disabled; keyboard order; pending submission disables actions; mocked 401 shows an alert and re-enables submit; reduced motion; email-verification navigation. `.local/login-design/interaction-checks.json`. Initial smoke command had PowerShell Unicode pipe encoding in its locator; corrected the test selector, no application change. |
| Static review | `uiux audit --target frontend`: exit 0, warnings from React HTML entry (heading supplied at runtime) and pre-existing generated Playwright report. `git diff --check`: PASS. |

Final screenshots: `.local/login-design/qa-final/desktop-page.png`, `tablet-page.png`, `mobile-page.png`. Local preview: http://127.0.0.1:5173 (Vite). This preview's backend proxy expects port 8000; the real identity tests ran against the isolated test server at port 8092. No production backend was started.

## Limits and review

No engineering.json found; used repository commands. No TSX lint gate configured (root ESLint applies only to frontend scripts). Full unrelated banking/security/backend suites were not rerun for this presentation-only scope. Self-review completed; no independent reviewer dispatched. No WCAG certification claimed.

The managed `uiux run start` command was rejected by automatic tool policy with only `blocked by policy` supplied as reason. Used the standalone read-only `uiux qa` screenshot/check workflow instead; no managed-run completion claimed. Two visual assessments, one repair batch.

Unslop skill not found in the searched installed locations. The short introduction is planned by the user, not implemented in this scope. Login has a brief reduced-motion-aware entrance; no intro delay or playback dependency.

Other existing working-tree changes were preserved. Rollback: restore only this task's Login.tsx changes and remove LoginShell.tsx/login.css if no subsequent work depends on them; do not reset the working tree.
