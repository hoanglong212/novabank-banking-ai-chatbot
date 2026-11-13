# Sharp vector intro and login

## User decision and implementation

The previous v11 implementation preserved 1280×720 video pixels, but raster frames and the 560px-wide login crop blurred when enlarged. The user approved a vector reconstruction, accepting small visual/timing differences from v11.

- Replaced the intro's raster sequence with 90 Lottie shape layers and outlined typography. No image assets or browser font dependencies. Changed the existing lazy runtime to `lottie_light` with SVG rendering. Kept skip, Escape, replay, session memory, reduced-motion and recovery bypass, timeout/error fallback, and cleanup.
- Removed raster frame preloading. Active animation is approximately 296 KiB versus 10.43 MiB. Unused legacy assets remain on disk but are not requested.
- Replaced the login screenshot with semantic HTML headings/wordmark and `AuthArtwork` CSS/SVG account, chart, sample code and bill tiles. Retained v11's violet palette and split composition. The sample code is decorative and cannot initiate a payment.
- Mobile intro framing crops only empty margins and keeps the artwork centered. Device-scale-independent SVG paths stay sharp when enlarged. Existing app business/authentication logic remains unchanged.

## Verification

- Regression test was observed failing before the vector implementation because only a canvas existed. The completed test verifies SVG paths, no SVG image nodes, no raster network requests, desktop DPR 2, mobile centering, the semantic login heading and no screenshot image in the login panel.
- All five targeted intro tests passed (8.7s): normal playback, missing JSON fallback, high-DPR vector/no-image rendering, skip/replay, reduced-motion and recovery bypass. Evidence: `.local/vector-intro/green-final.log`.
- `npm run test:components` passed. `npm run build` passed. `git diff --check` reported no whitespace errors (only repository LF/CRLF notices).
- Opened intro frames 15, 45, 100, 130; mobile intro; login at 1280 and 1920; and a DPR 2 detail crop. Opened standalone UIUX desktop/tablet/mobile captures. Natural 1920×1080 capture verified all artwork opacity=1, no running entrance animations, and sharp text/geometry. Repeated full-page capture after viewport resizing can restart/fade compositor layers in the screenshot tool; the natural viewport capture and DOM metrics confirm final runtime visibility.
- The standalone static audit reports only the existing React-entry h1/generated-report warnings. Standalone browser QA reports its runtime gate false because React development StrictMode intentionally aborts the first intro JSON request. This has not been relabeled an all-green UIUX run. Custom browser capture has zero page errors.

## Scope and limitations

This is a vector recreation, not an exact pixel copy of the MP4. Icons, orbit motion and progress milestones have small differences. No new dependency/service was installed. No independent reviewer was dispatched; local self-review checked layer ordering, path data, cleanup, accessibility and scope.

Full configured Playwright E2E suite: **25 passed (4.6m)** on the final build (`.local/vector-intro/e2e.log`). The count changed from 26 because two raster-specific tests were replaced by one vector/high-DPR/no-image test. Final animation size: 302,562 bytes (46,561 bytes when gzip-compressed); 90 shape layers, zero image layers/assets, 4.5 seconds.
