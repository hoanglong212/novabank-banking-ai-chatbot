# T10 local Prompt Guard measurement

User-approved scope: implement the six steps in the T10 request on
`week8/t10-promptguard-run`, based on `week8/integration` at `b5145ac`.
Execute inline, then obtain one independent branch review. No model downloads,
Hub credentials, attack-matrix execution, live-bank changes, or merge.

1. Verify both local CPU models, record probes, versions and artifact hashes.
   Keep weights ignored. Add the requested attribution in NOTICE.
2. Test and implement compatibility with the original PG2 generic binary labels;
   retain strict rejection of other label maps. Configure model path and threshold
   by environment. Check chain order, B/D enablement, A/C disablement and outage
   fail-closed behavior. Existing chain/event implementation remains authoritative.
3. Add a reproducible detector-only benchmark and regression tests for corpus
   integrity, deterministic paired-language splitting, calibration-only threshold
   choice, missing prediction coverage, F1/FPR and latency. Freeze half the rows
   for calibration before inference; report the other half separately. Qwen's
   existing Boolean classifier has a fixed decision rule, not a probability.
4. Reuse the exact historical 100 benign tasks and synthetic seed in four fresh
   25-task cohorts, with the measured detector enabled in D. Collect per-stage
   signals, errors, utility and unchanged financial-state assertions. Never
   approve/confirm proposals. Keep raw private logs under ignored .local/.
5. Publish sanitized evidence and T10_PROMPTGUARD_RESULTS.md. Run backend and
   research pytest plus Ruff, review the diff, commit and open an unmerged PR
   into the base. Report actual outcomes and inherited limitations honestly.

## Review focus and rulings

- Generic LABEL_0/LABEL_1 is the locally supplied base config; explicit semantic
  maps must still work, including reversed indices. Reject three-label models.
- Local loaders must pass token=False, local_files_only=True and disable remote
  code/pickle. A missing model still denies and must not fall through to Qwen.
- Threshold must be finite and inside (0,1); config errors must fail closed.
- Accent/unaccented counterparts stay in one split; related templates remain a
  limitation. No held-out outcome may affect threshold selection.
- Ruling: the existing 52-row file contains literal encoding damage, not merely
  terminal mojibake. Preserve it and measure it as a legacy control. Add an
  explicitly reconstructed UTF-8 version with the same IDs, labels and channels
  for meaningful language strata; do not describe it as recovered original text.
- Ruling: this checkout has neither docs/plans/vong-2-agent.md nor R1 artifacts.
  Detector-only text classification and benign utility do not run the attack matrix.
- Base has a previously reported account-target-binding P1 outside this T10
  change. Do not claim the whole application is security-approved.

## Ledger

- Clean branch created; models untracked; both CPU models passed two raw probes.
- Adapter regressions passed RED/GREEN; 6 actual local-model/API checks passed.
- Benchmark complete: 168 primary rows, frozen 84/84 split, plus 52 untouched
  legacy damaged controls per detector; no unavailable predictions. Benchmark
  v2 shares the actual app Qwen request; preliminary v1 retained locally.
- Benign rerun complete: exact historical 100 cases, 97 successes, zero
  unavailable, 3 PG false blocks among 10 screened tasks, 197 primary calls.
- Ruling: retain threshold 0.01 only as the measured lab threshold. Do not
  retune on utility outcomes or promote it to production; source JSON FPR is
  30%, despite zero benign false positives in the small text calibration.
- Backend 847 passed / 2 weight-dependent skips / 1 existing xfail; research
  42 passed; Ruff and whitespace passed. No dependency installation.
- Independent review by /root/t10_promptguard_review: no remaining P1/P2/P3.
  Corrected the NOTICE relative link identified during review.
- Release evidence is published under docs/release/week8-evidence/t10-promptguard.
  Final delivery is an unmerged draft PR into week8/integration; CI status is
  reported on the PR and in the user handoff, not inferred from local checks.
