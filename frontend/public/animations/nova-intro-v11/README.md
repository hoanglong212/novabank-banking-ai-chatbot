# NovaBank introduction — v11

Source supplied by the user: `Nova Intro v11 (1).mp4`, 1280×720, 30fps, 5.6s.

`animation.json` is a standard Lottie composition with 135 image layers. The accompanying `frames/` folder is required. Each lossless WebP is one original decoded frame, shown for exactly 1/30 second. This is raster Lottie, not vector artwork. The composition ends at 4.5 seconds, before the video reveals its noninteractive login mockup; the application then opens its real form.

Regenerate the frames from the supplied source using ffmpeg (from this directory):

```
ffmpeg -i "Nova Intro v11 (1).mp4" -frames:v 135 -c:v libwebp -lossless 1 -compression_level 4 -pix_fmt bgra -start_number 0 frames/frame-%03d.webp
```

Then run `node frontend/scripts/build-intro-lottie.mjs` from the repository root. The app uses the locally bundled `lottie-web` light canvas player, with lazy loading, bounded preloading, one play per session, explicit replay, skip/Escape, reduced-motion bypass and failure fallback.

The frames total approximately 10.43 MiB. Native resolution is preserved; desktop/mobile resizing keeps the original 16:9 image proportions. Large raster image sequences use more memory than the original MP4. No claim of resolution-independent vector fidelity is made.

The related authentication illustration at `/images/auth/nova-v11-panel.webp` is an original-source crop from 5.5s (560×650 at x=0, y=0). It is illustrative; the controls on the right are real React forms.
