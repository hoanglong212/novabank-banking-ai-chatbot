# Unified authentication redesign

Goal: replace the rejected login design with a premium light interface, large typography and soft motion across login, registration, email verification/resend, password recovery/reset and MFA code entry.

User chose: premium, light background, large typography, soft motion. Scope expanded with the supplied Nova Intro v8.mp4 reference: introduction precedes loading, then opens the real login. User asked whether a vector JSON conversion was necessary; explained that native SVG/CSS/React can reproduce the motion without Lottie or embedded video.

Architecture: AuthFlow owns a persistent AuthShell. Login and MfaSignIn render form content inside it. The shell animates a keyed stage panel, with shared presentation helpers/styles. Existing requests, validation, MFA methods, cooldown/expiry, stale-response protection and navigation remain intact.

Stack: React 19, TypeScript, CSS, Lucide, existing Playwright. No added dependencies or services. Preserve existing user edits in AuthFlow; snapshot before changes is in .local/auth-redesign-backup.

Directions: centered form alone is quiet but underuses desktop; dark illuminated portal conflicts with chosen light aesthetic; warm editorial canvas with a white form and restrained bank-card artwork matches the chosen direction. Select the third, using existing violet tokens with warm auth-only neutrals and Georgia display typography.

- [x] Replace the two competing shells with the shared light shell; common headings/actions; remove obsolete LoginShell/login.css created in the previous turn.
- [x] Bring all authentication forms into the shared layout. Use compact two-column registration on desktop and one column on mobile. Preserve labels/autocomplete/minimum password lengths.
- [x] Style the six-digit native OTP field, expiry/error/resend feedback, and focus. Keep one native input for paste, backspace, autofill and screen readers.
- [x] Add finite scene entrance, stage/field stagger, focus/hover/pressed feedback and loading animation, all honoring reduced motion. No delayed form submission.
- [x] Add IntroGate: 1.8s introduction, 1.2s loading transition (bounded font readiness), 0.4s exit. Once per tab, skip/Escape/replay; bypass recovery links, session notices and reduced motion. Active sessions never mount it.
- [x] Run build/components and identity/security/intro E2E. Inspect every stage at desktop/mobile, check overflow, reduced motion and OTP editing.
- [x] Record evidence and limitations; self-review the scoped diff. No automatic commit, dependency installation or subagents.

Review focus: registration height on mobile; long error/status text; heading focus after navigation; shell persistence; MFA expiry/cooldown and method switching; no credential leakage into artwork or screenshots.
