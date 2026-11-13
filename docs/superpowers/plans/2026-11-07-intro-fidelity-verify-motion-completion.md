# Validation and remaining fidelity limits

Implemented the source-derived Lottie update and six-cell verification presentation described in `2026-11-07-intro-fidelity-verify-motion.md`.

- Final Lottie: 234 vector shape layers, 1,131,934 bytes, 135 frames at 30 fps, no image layers and no image assets. Original cubic outlines and sampled QR modules are stored with provenance; motion/effects are reconstructed.
- `npm run test:e2e`: **27 passed (4.5 minutes)**, process exit 0, including real-backend identity/MFA/recovery checks and the new digit-motion tests. Log: `.local/verify-motion/e2e.log`.
- After the final N fade, orbital highlight length and checkpoint-position refinements, the five intro and two verification tests were rerun: **7 passed**, process exit 0. Log: `.local/verify-motion/final-focused-exit.log`.
- Final `npm run build`: TypeScript and Vite passed, process exit 0. Log: `.local/verify-motion/build-final.log`.
- `npm run test:components`: passed, process exit 0. Log: `.local/verify-motion/components.log`.
- Inspected the actual intro at seven frames and verification at 320px, 375px and desktop DPR 2. Native pointer replacement, leading zeroes, deletion, formatted paste and reduced-motion behavior were checked. Browser captures reported zero page errors. High-DPR intro playback completed at both 375px and 1920px; local headless animation-frame p95 was approximately 16.8 ms (not a device-wide performance guarantee).
- Standalone UIUX audit and QA ran. All three QA screenshots were opened. Static warnings concern the React HTML entry point and generated Playwright report. QA flags the development StrictMode cleanup's aborted intro JSON request; this is not reported as a clean QA gate. Normal playback, missing-asset fallback, skip/replay, reduced motion and recovery bypass passed dedicated browser tests. No independent reviewer was dispatched.

The result is **not pixel-identical to v11**. Light/shadow, particles, letter reveal, exact easing and some transitions remain reconstructed approximations. The earlier full-frame vectorization was rejected because it visibly posterized gradients. Only MP4 source is available, so the original editable layers and motion curves were not recovered. The login artwork was not redesigned in this change.

No dependencies or services were installed. Existing unrelated changes and legacy frame assets remain intact.
