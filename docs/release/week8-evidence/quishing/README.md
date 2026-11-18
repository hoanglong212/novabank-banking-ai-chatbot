# C3 payment QR evidence

Date: 2026-11-15. All accounts and money below are synthetic. No live demo database was read or written. Browser tests start fresh disposable servers on ephemeral ports, with an isolated random test-only QR signing key. That key is never printed or committed.

## Finding and correction

A valid HMAC only authenticated a QR payload; `account_name` and `add_info` still accepted URLs or instructions. Nine new regression cases initially failed: a validly signed QR containing `https://evil.example/pay` decoded with HTTP200, instruction-bearing names/memos decoded with HTTP200, generation normalized/truncated hostile text instead of rejecting it, and successful scan results lacked provenance.

`qr_security.py` now checks payment prose before generation normalization/truncation and after signature/schema verification at decode. Known URL schemes, domain patterns, instruction phrases/tool names (English and Vietnamese with or without accents), and invisible formatting controls are rejected with HTTP422 `UNSAFE_QR_CONTENT`. Payload text is not reflected in the rejection. Screening never fetches URLs or invokes a model. Safe payment prose remains data; ordinary Vietnamese billing notes still pass.

Successful decode returns `source_origin: 'qr'` and `qr_security` metadata: no flag, external-bank caution, reviewed text-field names and SHA-256 fingerprint of the already-verified signed payload. Leading account-number zeros, amount and bank fields are preserved. This metadata is **not** permission to pay, proof of identity, or a replacement for server-side new-payee detection.

QR UI now identifies the source and warns for external-bank recipients. OCR prefill carries `source_origin: 'ocr'`. No transfer is created by scanning; a user must open and submit the normal review flow. Transfer draft persistence/final confirmation provenance and centralized `qr_scanned` event logging require the root integration hooks described below.

## Verification

| Check | Result |
|---|---|
| New quishing cases + existing QR/product/guard backend tests | 32 passed |
| `npm run build` | Passed |
| `npm run test:components` | 19 groups passed |
| New real-browser quishing suite | 2 passed, latest 26.3s |
| Ruff on changed backend/test files and `git diff --check` | Passed |

The malicious browser case uploads actual PNG QR pixels containing an otherwise-valid server signature and an attacker URL. It observes HTTP422, no request to the attacker origin, no transfer/OTP POST and no payment review. `malicious-qr-blocked.png` and `malicious-bank.log` capture the outcome.

The positive browser case uploads a genuine external-bank QR, shows the QR-source and new-recipient caution, opens the ordinary transfer review and reaches the separate verification form. It stops before confirming payment and verifies the original 10,000,000 VND balance is unchanged. See `genuine-qr-review.png`, `genuine-qr-verification.png`, `genuine-bank.log`.

These are targeted regression observations, not proof that every possible quishing encoding is detected. Public-bank QR formats outside signed NovaBank `NBQR1` remain unsupported. Screenshots were visually inspected with animations disabled; no raw login-code video is committed.

## Reproduce

From repository root:

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_quishing_payment_text.py backend/tests/test_qr_browser_policy.py backend/tests/test_product_invariants.py backend/tests/test_guard_qr_langgraph.py -q
cd frontend
npm run build
node node_modules/@playwright/test/cli.js test tests/e2e/quishing.spec.ts --reporter=list
```

An isolated worktree can set `NOVABANK_PYTHON` to the existing project venv. No dependencies or browsers are installed by the tests.

## Root integration hooks

1. Add `source_origin?: 'manual' | 'qr' | 'ocr'` and optional `qr_security` to shared transfer-start data; persist/re-read origin in bank drafts. Treat client origin as a disclosure label, never authority. For stronger proof, revalidate the original signed payload or associate its fingerprint with a bank-owned scan record.
2. Render final confirmation provenance from persisted bank draft data, not a model response or client new-recipient claim. Detect saved/new recipients server-side independently of QR warning metadata.
3. Register `qr_scanned` in security-events allowed event names. In `routes_qr.scan`, log success or rejection with actor, outcome, `source_origin: 'qr'`, flagged boolean and optional fingerprint; do not record raw payload, links, account names, OTP or tokens. Commit logging even when returning a rejected scan.
