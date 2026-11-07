# QR Pay completion — 2026-11-08

## Follow-up: immediate personal QR

The user requested that My QR show the code immediately without amount/content fields. ReceiveQr now automatically creates an amount-free code for the first owned account, keeps download/sharing, and offers an account selector only when there are multiple accounts. Loading, empty-account, retry and stale-response handling remain. The earlier create form/button has been removed.

Verification: TypeScript/production build passed; the mobile product QR flow passed; the updated scan/automatic-receive test passed after correcting its expected seeded holder name to uppercase. The test checks that the generation request has only bank/account/name and that amount inputs and the create button are absent. The new mobile receive screenshot was opened and inspected. A concurrent rebuild changed the deployed asset hash, but the current served bundle was inspected and contains the immediate-QR change.

History confirms commit 29de3a1 used VietQR bank/generate/Quick Link services; baf4edd replaced this with private NovaBank QR before this QR redesign. The user subsequently chose to restore only the bank catalog and keep personal QR on the existing NovaBank demo accounts. This replaces the earlier pending scope question.

## Follow-up: VietQR directory restored

The backend fetches `https://api.vietqr.io/v2/banks`, validates/normalizes rows, deduplicates BINs and combines the live directory with the three existing demo banks. Successful results are cached in memory for 24 hours. Concurrent refreshes share a lock; failure keeps cached/demo banks and delays retry for 60 seconds. Personal NovaBank QR generation bypasses this fetch entirely and retains signed NBQR1 payloads. No real QR-generation or payment endpoint is called.

Only the two VietQR image hosts are accepted for directory logos and allowed by the image CSP. Other CSP directives remain scoped as before. OCR now matches exact short bank codes such as VCB and MB as well as full names; unrelated words containing those letters do not match.

Live browser verification discovered an existing nested-dialog bug: closing BankPicker propagated a React close event to TransferSheet and closed both. Sheet now handles only its own close event, and its close button is explicitly non-submit. The QR upload test now covers choosing a bank while keeping the transfer form open.

Backend directory/header/transfer/agent checks: **40 passed**. Component checks and production build passed. A live directory request returned **76 external banks plus 3 demo banks**. The existing local launcher was restarted with the same local-deploy script/database and persistent configuration; localhost:8080 reported healthy Ollama mode and the updated logo policy. Final browser validation: **10 passed (1.6m)**, comprising the 7 QR cases, 2 existing product cases and a local live-network smoke test. The live test verified the authenticated directory, actual loaded Vietcombank logo, selection without closing the transfer form, and an unchanged NBQR1 personal payload. Its screenshot was inspected. The deployed page returned HTTP 200 with the final compiled asset, and scoped diff whitespace checks passed.

The user explicitly authorized jsqr 1.4.0, tesseract.js 7.0.0 and Vietnamese/English recognition data. Installed exactly those direct package versions, with lockfile updates. No additional services were installed.

## Delivered

- Scan-first layout using the existing light/violet tokens, responsive at 375/768/1440px. The three actions appear in order: Mã QR của tôi, Chuyển tiền bằng hình ảnh, Tải ảnh lên.
- Explicit camera activation, native detector where available and lazy jsqr fallback. Camera tracks stop when another tool opens, the page hides, a code is found or the component unmounts. Permission/device errors offer upload instead.
- Receive/create/download signed NovaBank QR; QR image decoding from real PNG/JPEG/WebP pixels, followed by existing server validation and recipient review.
- Local Vietnamese/English OCR of bank/account text. Editable suggestions preserve leading zeros, reject ambiguous or malformed account strings, and match only the existing supported bank catalog. A review checkbox is required before opening the transfer form. OCR never submits a payment.
- Recognition progress, retry, manual entry and cancellation. A disposable supervisor worker owns Tesseract initialization and its child worker, allowing cleanup even if language loading fails or the user cancels during initialization. Closing/changing images aborts the previous task.
- Pinned Apache-2.0 language data under public/ocr/lang; provenance and licenses included. prepare:ocr copies locked worker/WASM assets during dev/build. All recognition assets load from the app origin; the image remains local.
- Same-origin camera and worker permissions, with the WebAssembly-specific CSP allowance. No general unsafe-eval or external script hosts were added.

## Verification

- `npm run build`: passed, TypeScript and production Vite build. Production build contains separate OCR worker and lazy QR decoder chunks.
- `npm run test:components`: passed, including account parsing with leading zeros, letter/digit ambiguity, multiple accounts, phone/amount exclusion and unknown banks.
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_qr_browser_policy.py backend/tests/test_product_invariants.py -q`: **6 passed**.
- Playwright QR Pay and existing product flows: **9 passed (1.6m)** on an isolated backend at 8098, disposable database and `.local/qr-pay/dist`. Test bodies match the source files; only helper database paths and server configuration are isolated. Shared port 8092 was left alone.
- Browser checks include actual JPEG QR pixels with PNG metadata removed, actual camera-stream QR pixels with BarcodeDetector absent, denied-camera handling, track cleanup, real bilingual OCR preserving `001234567890`, explicit recipient review without transfer POSTs, local-only OCR requests, no CSP violations, failed language-load cleanup, cancellation and intact manual edits.
- Authenticated screenshots inspected: desktop/mobile scan layouts and mobile OCR result; earlier receive and tablet captures also inspected. No horizontal overflow in tested widths. The mobile sheet scrolls to its confirmation controls.
- Current localhost:8080 returned HTTP 200 with the new production build, local worker JavaScript and updated camera/CSP headers. No backend restart was needed during final verification.
- Scoped `git diff --check`: no whitespace errors (only Windows line-ending notices).

## Limits and process notes

QR payment support remains the existing signed NovaBank simulation format. Supported transfer banks remain the existing catalog. OCR results are suggestions; fuzzy photographs or unsupported bank names require correction. Physical camera hardware was not exercised; camera behavior was tested using browser MediaStreams carrying real QR pixels, plus permission denial.

The UIUX managed run was previously rejected by automatic approval review (`blocked by policy`); it was not retried or bypassed. Standalone audit/QA and authenticated Playwright visual inspection were used, without claiming a passed managed UIUX gate. The standalone unauthenticated QA limitation is recorded in the earlier progress checkpoint.

Unrelated working-tree changes were preserved. No commit, push or external deployment was performed.
