# Nova v11 — vector reconstruction

Self-contained standard Lottie JSON. 1280×720 composition, 30fps timing with subframe interpolation, 135 frames / 4.5s. All 90 layers are shape layers; `assets` is empty. No image frames or external fonts are required. Lettering is outlined geometry, gradients and icon artwork are scalable vectors.

Rebuild with `node frontend/scripts/build-vector-intro.mjs`. Outlined system typography is stored in `frontend/scripts/nova-intro-outlines.json`; regenerate it on Windows with `frontend/scripts/export-intro-type.ps1` only when changing the text. No font package or new runtime dependency is required.

The user explicitly chose a vector reconstruction for sharpness, accepting small differences from `Nova Intro v11 (1).mp4`. This is not a lossless conversion of that video: orbit paths, icon details and progress milestones are reconstructed. The broad composition, violet palette, core N, outlined wordmark and intro → loading → live login sequence follow v11.

Playback uses the existing lottie-web light SVG renderer. Mobile framing enlarges the artwork while cropping empty composition margins. Loading percentages are decorative animation content, not measured network download progress; the screen-reader status describes opening the app without exposing these illustrative percentages.

Active animation JSON: approximately 296 KiB, replacing approximately 10.43 MiB of active raster frames. Older raster directories are retained but no longer requested by this UI.
