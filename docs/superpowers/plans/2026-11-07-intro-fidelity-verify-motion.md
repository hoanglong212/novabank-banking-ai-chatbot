# v11 source fidelity and verification digit motion

The user rejected the previous hand-drawn intro as inaccurate and requested animation for each verification digit. They confirmed that only the MP4 exists; no editable vector or motion source is available. This supersedes the earlier assumption that a broadly similar reconstruction was sufficient.

## Changes

- Vectorized the original v11 frame at 1.5 seconds with Adobe's image vectorization tool. The complete trace posterized the background and damaged small text, so it was not shipped as a full-frame replacement.
- Retained selected original cubic paths for the N, NovaBank wordmark, question mark, search, Vietnamese currency and bill symbols. The QR module pattern was measured directly from the original frame. Provenance is stored in `frontend/scripts/nova-intro-source-paths.json`.
- Reconstructed the two tilted orbits, measured icon positions at seven reference times, completion colors/checkmarks, expanding rings, the continuous percentage display and the actual loading messages. The output remains a Lottie shape animation with no bitmap assets.
- Replaced the verification field's visual presentation with six animated cells around one native labeled input. New/replaced digits animate independently. Native keyboard editing, leading zeroes, paste, numeric keyboard hints, one-time-code autofill semantics, focus, invalid/disabled states and reduced motion remain supported.

## Fidelity boundary

This is source-derived vector geometry with reconstructed motion, not recovery of an original Lottie project. Soft shadows, particles, letter reveal, easing and some transitions still differ from the MP4. Do not describe it as pixel-identical or claim that MP4 automatically converts into the original vector layers. The login illustration was not redesigned again in this change.

## Validation

Evidence lives in `.local/verify-motion/`. The focused verification tests were first observed failing against the old field, then passed after the new component and explicit accessible label were implemented. Visual captures cover 320px, 375px and desktop at DPR 2; pointer replacement of a middle digit works. Intro captures cover frames 15, 30, 45, 75, 105, 125 and 130 with zero browser page errors and zero SVG image elements.

Full configured build, component and E2E outcomes are recorded in the completion note after they finish. No dependencies or services were installed. Earlier unrelated working-tree changes were preserved.
