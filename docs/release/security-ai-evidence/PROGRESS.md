# Security / AI acceptance — 2026-11-01

Follow-up: the user authorized SEC-10 dependency updates and local code finalization. See [the next-round report](../sec10-upgrade/REPORT_VI.md); entries below preserve the previous round.

Step 0: local commit `baf4eddb96f01f03a0c54d70e25e25f32210dd15` on `feat/banking-core-foundation`; no push.
Reviewed snapshot and encrypted read-only backup: see STEP0_REVIEW.md. Restore/reconcile validated in a disposable directory.

Current scope: SEC-04/06/09/10, AI-05/07/10/15, PI-02/04 only. No dependency installation, no demo DB writes, no research rerun.
Test-first probes completed. Confirmed/fixed: PII on model wire and traces, missing stop reasons, invalid-argument explanations, reset/verification query tokens in access logs, memo normalization and blocked font console errors. No expectations relaxed; fixture corrections documented in REPORT_VI.md.

Final: 358 pytest passed, 1 failed (SEC-10); 17 component groups passed; 16 E2E passed; isolated reconcile balanced; final raw-log scan clean for configured secret patterns. SEC-10 remains unresolved with certifi Critical and three Moderate advisories plus unavailable pip-audit. New work is uncommitted; no push. Full evidence and deferred scope: REPORT_VI.md.
