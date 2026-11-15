# T6 calibration evidence handoff

| Acceptance | Observed evidence |
|---|---|
| At least 100 legitimate tasks reach actual D/model execution | Registered 100-case corpus in four 25-case cohorts, plus 20-case supplement; 191 + 40 actual primary Qwen calls |
| Risk bands and new-recipient cooling measured | 100 legitimate proposals: all expected bands; supplement exact score/band/cooling 20/20 |
| Known-payee and high-amount strata are genuine | Three ordinary verified setup transfers before baseline; bank-owned settled-transfer trust, funded account, no direct balance/trust edits |
| No measured money/account/product effects | Four cohort business fingerprints match seed; supplement matches post-setup baseline |
| Failures retained | Original 70 quota rejections; nine unavailable source reads; unpaid-bill invalid model argument; outage-to-risk/quarantine coupling reported to root |
| Evidence has source identity and bounded claims | Matching cohort source hashes, raw-model hashes, model inventory, explicit pre-fix snapshot scope in [report](../../week8/T6_BENIGN_CALIBRATION.md) |

Changed files: `docs/release/week8/T6_BENIGN_CALIBRATION.md`, this evidence directory's JSON/CSV/metadata files, and local runner/inspection/publication scripts under `.local/week8-completion/benign-calibration/`. No production code, policy weights or shared tests changed in this lane.

Actual validation: four cohort collectors and supplement exited 0 after collection; publisher assertions passed; `ruff check .local/week8-completion/benign-calibration` passed; local script compilation passed; release JSON/link checker reported 66 links and no broken targets at handoff. Collector success does not convert unavailable/failed utility cases into passes. No full backend/frontend suite is claimed for this artifact-only lane; root owns integration checks after its separate application fixes.

Author: `/root/week8_benign_calibration`. Independent/root integration review is pending. The default-score experiment is complete within the documented scope; healthy Prompt Guard read utility and later app changes are not validated here. Rollback removes this evidence package and leaves the application unchanged. Original experiment artifacts remain in ignored disposable directories.
