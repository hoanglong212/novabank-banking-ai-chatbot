# QR Pay — historical checkpoint before authorization

**Superseded:** the user subsequently approved the dependencies and language assets. See `2026-11-08-qr-pay-completion.md` for the implementation and final verification. The remainder records the earlier checkpoint, not the current state.

The user clarified that image transfer means reading a bank name and account number from an image, separately from QR image upload.

Implemented and visually inspected the scan-first light layout at 375, 768 and 1440px. Primary actions are in the exact requested order: Mã QR của tôi, Chuyển tiền bằng hình ảnh, Tải ảnh lên. Receive/create/download, signed PNG decode, text decode and recipient review remain functional. Image transfer currently provides a local image preview and manual recipient fields; **automatic OCR is not implemented yet**. Do not describe it as completed OCR.

Camera lifecycle currently uses native BarcodeDetector capability checks. It explains denied/unavailable access and stops tracks when another tool opens, the tab hides or the component unmounts. Windows browsers need the proposed jsqr fallback. A server header that disabled all cameras was corrected to same-origin camera permission; microphone/geolocation remain disabled. Local blob image previews are allowed. The already-running backend was not restarted, so its existing headers remain until restart; the Vite page is served separately.

Requested explicit authorization for jsqr 1.4.0, tesseract.js 7.0.0 and local English/Vietnamese OCR data because the user's AGENTS instructions prohibit automatic dependency installation. **No response/authorization received yet; no packages or language files installed.** The existing lottie authorization does not cover these packages.

Prepared a pure OCR-text interpretation helper with tests for leading zeroes, ambiguous numbers, phone/amount exclusion and unknown-bank handling. Once approved, connect real local OCR, load workers/language assets from the app, validate recognition against synthetic image fixtures, add jsqr camera/image fallback, and adjust the minimum required worker/WASM CSP directives. Do not add external image processing or automatically submit transfers.

## Checks

- TypeScript and Vite builds passed while constructing the layout. Final scoped TypeScript check follows this note.
- Component checks passed, including the new payment text interpretation cases.
- Backend header regression reproduced before the fix; afterward **6 tests passed** across the new header test and existing product invariants (`.local/qr-pay/policy-green.log`).
- Initial QR layout/denied-camera browser checks: **2 passed**.
- Shared port 8092 was occupied during subsequent runs. It was not stopped or reused. An isolated disposable backend on 8098, isolated compiled assets and copies of the unchanged test bodies/helpers were used: **6 E2E tests passed (1.1m)**, covering product flows, QR ordering/receive, denied camera, signed image upload/review and camera-track cleanup (`.local/qr-pay/isolated-flows.log`). No working demo balances were changed by these tests.
- Screenshots under `.local/qr-pay/scan-{375,768,1440}.png`, `receive-panel.png` and `image-panel.png` were opened and inspected. The initial image-panel capture was mid-animation; it was recaptured after settling.
- UIUX managed `run start` was rejected by automatic approval review with `blocked by policy`; it was not retried or bypassed. Standalone audit and QA ran. QA reaches the sign-in gate without an authenticated browser context and flags the known development StrictMode aborted intro fetch; it is not a passed QR-specific QA gate. The authenticated Playwright captures and tests above are the QR evidence. All three standalone screenshots were also opened.

The task is not fully complete until OCR and Windows QR scanning are implemented and tested, or the user explicitly chooses the layout-only option.
