# Week 7 execution ledger — 2026-11-05

Source: `C:/Users/Admin/Downloads/playbook-chi-tiet-week7.md`. Execute WS0–WS9; week 8 phase 2 is excluded.

- WS0: local tag `pre-week7`, branch `week7/integration`; baseline checks completed (logs in `.local/week7-baseline-*`). Existing README edit preserved. No remote push.
- WS1: original SYSTEM OVERRIDE prompt received; input guard regression and independent recipient-binding regressions pass. `BYPASS_NOTE.md` distinguishes the observed regex defect from the unverified historical bypass. Original demo profile/log remains missing.
- WS2: completed full Qwen run (2,070 observations, five repetitions, 96 execution errors, 220 exclusions) and separate 150-observation post-fix regression. On matched trials, errors fell from 96 to 6; all 90 savings-trace upstream failures disappeared. Raw full results remain unchanged. See `EVALUATION_STATUS.md`, `KNOWN_FAILURES.md` and `postfix-regression/comparison.md`. The paths retain binding; legacy-off is not a true gateway-off profile. Full mock reference is retained separately.
- WS3: four read-only staff tools, five-role permission tests, source screening, and staff assistant UI implemented. Real Qwen browser checks passed for admin and Alice. See `RBAC_MATRIX.md`.
- WS4: demo-only outbox implemented; transfer responses no longer contain `demo_otp`; resend/consumption invalidate old codes. UI recording and actual response JSON saved; Caido capture pending.
- WS5: isolated loopback fetch harness, exact URL allowlist, timeout/body limits, and scripted bank-boundary probe completed. Real Qwen experimental fetched the lab page without proposing payment; default lacked a fetch tool. Research VM/payload unavailable; app QR schema remains unchanged.
- WS6: transfer/review/OTP/receipt, approval, outbox, staff assistant and QR draft deep links implemented. Latest full E2E: 20 passed, including a new-history selection race regression. History API used without installing a routing dependency.
- WS7: create_app, route extraction, compatible agent package and request correlation completed. With user authorization on 2026-11-06, Ruff 0.14.3 and ESLint 9.39.1 were installed in the venv/npm cache; both configured correctness lint commands passed locally. See `lint-checks.json` for scope and counts. Remote CI has not run.
- WS8: `CRYPTO_AUTHZ.md` completed; optional new-recipient cooldown not implemented.
- WS9: full Qwen CSV/tables, paired post-fix comparison, seven HTML slides, outbox/QR/admin media, role-check JUnit XML and raw response evidence assembled. The evidence watcher finished publishing; the updated result slide was visually checked. Caido/VM and independent review remain unavailable.

## Decisions

- Use the supplied detailed playbook as the accepted implementation plan. Companion overview is absent.
- Do not install dependencies/services automatically. React Router remains absent; the app uses a small History API router with existing React. Ruff/ESLint were installed only after explicit user authorization; package manifests and lockfiles remain unchanged.
- User authorized qwen2.5:7b download. The original Ollama daemon listed no models because it could not resolve the model location; model files exist on D:. A separate loopback Ollama server at port 11435 serves Qwen. The corrected local bank uses port 8081 and agent port 8094; ports 8080/8093 remain the older instance.
- Public demo outbox is enabled only by explicit `ENV=demo`, including unauthenticated login MFA. This is a local simulated mailbox, not a production email channel.
- App baseline already binds transfer arguments independently; harness baseline is different. Never remove app safeguards to make an off/on comparison look stronger.
- VM/Caido access, historical demo profile and independent review are not available. Record missing evidence honestly.
- Automatic approval review rejected the process-stop/restart verification command with `blocked by policy`. The previous application was left running. The start script successfully launched the corrected application on separate ports with a SQLite backup of the fictional demo DB. Stop/restart of an existing instance remains unverified.
