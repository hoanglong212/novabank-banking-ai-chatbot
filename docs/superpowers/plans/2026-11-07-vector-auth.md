# Vector sharpness repair

User approved rebuilding the intro as true Lottie vectors, preserving the v11 composition/motion with possible small visual differences. Root cause: a 1280×720 video-frame sequence and 560px-wide screenshot panel were being enlarged. Lossless storage preserves those pixels but cannot recover detail.

1. Replace login screenshot with semantic HTML text and scalable CSS/SVG artwork matching v11 (violet, same two-column composition and sample account/QR/bill tiles).
2. Generate a self-contained Lottie using shape paths, outlined typography and keyframes. No raster image assets. Render with the existing lottie-web SVG player; keep lifecycle, skip/replay, reduced-motion/recovery bypass and error fallback.
3. Test that no image layers/network frame requests remain; inspect at desktop, mobile and high DPR/zoom. Run actual build, component checks and relevant/full configured E2E checks.

No new dependencies or services. Existing approved lottie-web is reused. Prior unrelated working-tree changes remain intact.
