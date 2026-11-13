# Nova v11 introduction and authentication

Superseded for rendering sharpness by `2026-11-07-vector-auth-completion.md`: the user later explicitly selected true vector Lottie and HTML/SVG login artwork instead of video-frame assets.

The final user direction supersedes v10/cyan: restore the old violet app colors, use original-frame Lottie for v11, and follow the login shown in v11 too.

## Implementation

- Original decoded frames 0–134, 1280×720 at 30fps, lossless WebP, Lottie image layers. 4.5s, 10.43 MiB of frames. The mock form baked into the video's tail is replaced with live authentication controls.
- Actual pinned lottie-web 5.13.0, explicitly approved by the user. Lazy-loaded light canvas build avoids the full player's expression/eval machinery. Validate all images before playback; bounded preloading, missing-asset/timeout fallback, destroy/abort cleanup, ResizeObserver, skip/Escape/replay, reduced motion and recovery bypass.
- Global app tokens and this task's other cyan replacements reverted to their original violet values without reverting pre-existing unrelated work.
- Login rebuilt around the v11 split layout, white/ivory form surface, sans-serif typography and violet pill action. Left illustration is a faithful crop of the user-supplied frame, with meaningful alternative text. No nonfunctional Face ID or language control was added. Existing username authentication, demo accounts, registration, recovery, verification and OTP remain live.
- Tablet/mobile use the compact single-column form. Persistent shared shell and soft transitions carry through all auth states.

## Evidence

- Source and exported RGBA frame hashes: all 135 match (`.local/intro-v10/v11-source.md5`, `v11-export.md5`).
- Actual Lottie canvas at frames 15, 45, 105, 134: exact pixel matches in the top 1280×640 source region; the lower strip was excluded because it includes the independent Skip button (`.local/intro-v11/canvas-fidelity.json`).
- New missing-asset regression observed red before implementation; resize regression observed red before ResizeObserver fix.
- Visual matrix: 27 states at 375/768/1440, no horizontal overflow, one form heading, no page errors; OTP editing, wrong/expired states, persistent shell and reduced motion checked. Opened contact sheets for all nine states. Some animation-disabled screenshot captures suppress already-finished image/heading layers; natural screenshot confirmed opacity=1 and correct rendering (`register-natural.png`).
- Standalone UIUX audit: only static React h1/generated-report warnings. Standalone browser QA checked labels/overflow/alt/headings, but reports `ERR_ABORTED` for the development StrictMode effect's intentionally cancelled intro JSON fetch. This is not reported as an all-green UIUX run. Managed orchestration was unavailable as previously recorded.

## Limits

Raster artwork preserves source pixels, not vector scalability. The sequence has a higher download/decode-memory cost than MP4. Timing follows the 30fps source on an unloaded browser; slow devices can drop display frames. A user may skip and reduced motion bypasses playback. The reference's account balance/QR are illustrations, not the logged-in account.

Automatic approval review rejected recursive cleanup of the task-created, unused v10 asset folder with `blocked by policy`; it remains on disk and is not referenced by the running UI. No workaround deletion was attempted.

No independent reviewer was used. Local self-review covered asset paths, lazy loading, cleanup, failure handling, accessibility and preservation of auth logic.

## Verification results

- `npm run build`: passed; light canvas runtime is a separate lazy chunk, with no full-player eval warning.
- `npm run test:components`: passed all configured checks. An intermediate CJS harness failure from importing Vite environment metadata in AuthShell was fixed by using the app's existing root-based asset paths.
- Full configured Playwright suite: **26 passed (5.2 minutes)**, including real banking, registration/recovery, MFA, intro error/resize/replay, security and Week 7 flows (`.local/intro-v11/e2e.log`).
- Final natural-capture visual matrix: **27 states passed**, including the refined single-column tablet breakpoint (`.local/intro-v11/auth-final/report.json`). Opened final tablet login, desktop registration and MFA error captures to confirm the earlier screenshot-animation artifact was absent.
- `git diff --check -- frontend`: no whitespace errors (repository line-ending notices only).
- Source SHA256: `6AC6CABD5EBFC6B11FAFD73853DD1BD6D93333B50CF8DA1CF8882FB443027441`.
- Final rebuild after the tablet breakpoint change: passed (`build-final.log`). Attempted rerun on the disposable E2E port was blocked because 8092 was occupied; no foreign process was stopped. The three UI-only responsive/invalid-link tests were then run against the existing Vite app with a local config: **3 passed (24s)** (`responsive-final.log`). They do not mutate the backend. The log includes only the environment's FORCE_COLOR/NO_COLOR warning.
