# Week8 evidence index

All banking data in these artifacts is synthetic. Missing, unavailable and excluded measurements remain explicit. Current outcomes and counts are in [RESULTS.md](../week8/RESULTS.md); the earlier report and raw outputs are preserved.

- [Continuous capture report](../week8/CAPTURE_COMPLETION.md) and [capture index](completion-captures/README.md): real MFA flow, malicious QR rejection and genuine QR through recipient-bound TOTP to the separate email OTP screen. New artifacts are actual continuous WebM recordings with derived GIFs, with secret inputs masked.
- [Genuine QR email-OTP frame](completion-captures/04-genuine-qr-email-otp.png) and [video](completion-captures/quishing-genuine-email-otp-continuous.webm): one email challenge, unchanged balance, no confirmation request.
- [Actual Caido history](completion-captures/caido-http-history.png), [401](completion-captures/caido-401-anonymous.png), [403](completion-captures/caido-403-customer.png), [404](completion-captures/caido-404-foreign-conversation.png), [HTTP/source metadata](completion-captures/caido-api-checks.json). Dedicated temporary project, three negative cases and two owner-positive controls; no claim that every API matrix observation used Caido.
- [API route matrix](../week8/API_TESTS.md), [original summary](../week8/api-summary.json), [redacted TestClient examples](../week8/api-http-examples.http): 128 routes, 452 passed observations, 128 explicitly inapplicable cells.
- [100-task benign calibration and 20-case supplement](../week8/T6_BENIGN_CALIBRATION.md): 100 proposals in expected risk bands; the old snapshot's availability/interface failures remain recorded.
- [T9 utility](spotlighting/README.md): original 80 calls plus 40 real Qwen3 calls. Requested models now covered for narrow off/on field-reading utility.
- [Qwen3 provisioning](qwen3-provisioning.json), [readiness/full-matrix plan](../week8/MODEL_READINESS.md), [final-source Qwen3/D positive demo](live-positive-demo-qwen3.json). Dashboard/agent balance 80,770,000 VND; cap changes only after human approval and bank OTP.
- [Earlier Qwen2.5/D positive demo](live-positive-demo.json), preserved with its original source hashes.
- [T10 detector evidence](t10-qwen-actual.json): Qwen 52 synthetic Vietnamese samples; licensed Prompt Guard models remain unavailable, even though the runtime is now installed.
- [T11 serial real calls](t11-live-recheck.json), [earlier timeouts](../week8/t11-live-evidence.json); schema validity is not demonstrated semantic accuracy.
- [Historical realistic-data N=10 subset](../week8/T12_REALISTIC_RESULTS.md), [CSV](../week8/t12-realistic-results.csv), [metadata](../week8/t12-realistic-metadata.json). 336 records, 137 eligible attacks, four benign controls; not the full final-source matrix.
- [Supplementary exact-foreign-balance recheck](g2-exact-fact-recheck.json): 80 retained G2 artifacts, 60 measured/20 unavailable; no changed result, no fresh inference or rewrite of historical evidence.
- [Five-layer slide](gateway-five-layers.html), [PDF](gateway-five-layers.pdf), [realistic seed](realistic-seed/README.md), [preview dashboard](local-preview-dashboard.png).
- [Historical MFA slideshow](mfa.gif), [historical quishing slideshow](quishing.gif): these older GIFs remain screenshot sequences and are not relabeled as continuous recordings. Historical genuine QR capture stopped at PIN; the new email-OTP recording closes that gap.
- [Current verification/source hashes](../week8/verification.json), [independent completion audit](../week8/COMPLETION_AUDIT.md), [failures and corrections](FAILED_ATTEMPTS.md).

The user confirms original design/transcripts do not exist. [The new design baseline](../../thiet-ke-gateway.md) describes implemented code; synthetic mentor cases are not historical incident transcripts. The extra C attack-demo action was rejected by automatic safety review for possible cybersecurity risk and was not retried to evade review; no such artifact is claimed.

New-payee trust comes from bank posting/settlement history. UI source-origin labels are not cryptographic capture proof. OTP-based authentication is not claimed to be phishing-resistant. This package does not establish universal absence of bugs or superiority over unmeasured systems.
