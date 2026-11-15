# Week8 completion evidence and limitations

This is an evidence map, not a declaration of 100% plan acceptance. Current actual check counts and remaining gates are in [RESULTS.md](RESULTS.md), with machine-readable source/log hashes in [verification.json](verification.json). Earlier measurements remain preserved in their original artifacts.

| Acceptance area | Implementation/evidence | Status |
|---|---|---|
| Dashboard and assistant financial consistency | Bank-owned rendering, per-field disclosure checks; backend financial regressions, full browser suite and real Qwen2.5/Qwen3 balance demos | Verified within stated cases |
| T1–T8 authority/policy/risk/approval/quarantine | Backend modules/tests; [independent audit](COMPLETION_AUDIT.md), [100-task calibration and supplement](T6_BENIGN_CALIBRATION.md) | Implemented/tested; healthy detector utility still unmeasured |
| T9 requested models | [120-call combined field-reading evidence](../week8-evidence/spotlighting/README.md), including 40 Qwen3 calls | Narrow compatibility measured |
| T10 three-detector comparison | Local-only adapter and [isolated runtime](MODEL_READINESS.md); Qwen 52 synthetic samples | Incomplete: human Meta acceptance/licensed base/VI weights and inference missing |
| T11 isolated ticket model | Enum-only primary boundary, encrypted human-only summary, two serial live schema checks | Implemented; broad semantic accuracy unmeasured |
| T12 final-source full matrix | Corrected v4 scorer, immutable final source on D:, 7,600 planned observations; historical336-row subset | Incomplete: plan-only final matrix and unsupported QR-to-agent channel are not successful measurements |
| C3/C4 | [Continuous genuine QR→email OTP, malicious QR rejection and full MFA recordings](CAPTURE_COMPLETION.md) | Captured with real assertions and synthetic data |
| C5 | [128-route API matrix](API_TESTS.md), three actual Caido denial cases plus owner controls | Measured; not exhaustive value/concurrency coverage |
| C6 |50 synthetic customers / 125 accounts; reconciled seed; OTP-confirmed transfer-cap functionality | Functionality verified; full T12 dataset rerun incomplete |
| T0/T13/C7 design/history/package | New [current design](../../thiet-ke-gateway.md), review, reports, slide, failure notes, continuous/Caido artifacts | Original history confirmed nonexistent; specified extra C attack GIF unavailable after safety rejection |

## Follow-up source changes

The follow-up changes `backend/app/agent/agent_access.py`, `agent/policy.py`, `agent/agent_guard.py`, `risk/scorer.py`, `routes_agent.py`, `agent_service/main.py`, `research/week8_core.py`, `research/week8_runtime.py` and `scripts/week8_evaluate.py`, with focused regressions for policy actions, run failure, bill filtering, detector outage, Qwen3 transport and financial-disclosure scoring. The larger Week8 worktree already contained intentional changes; no bulk reset, stash, commit, push or merge was performed.

The independent reviewer `/root/week8_acceptance_audit` reproduced four original integration/scoring findings and rechecked their corrections. Its follow-up reviewed outage/bill/Qwen3 changes and independently ran 20 affected tests successfully, with no new concrete defect found. This is a scoped code review, not a penetration test or universal guarantee. The capture/calibration lanes independently preserved their raw failures and source identities.

Exact commands and observed statuses are recorded in [RESULTS.md](RESULTS.md). The configured backend/research/browser/component suites, Ruff and whitespace checks are used; no missing `engineering.json` gates are invented. Current `verification.json` identifies logs, scope and hashes. No model is counted as working merely because its adapter or runtime exists.

## Local operation and rollback

The updated synthetic preview is at `http://127.0.0.1:8081`, paired with agent service 8094. `.local/week8-preview/latest.json` identifies its synthetic database and owned process IDs. The existing live deployment on 8080/8093 and `.local/local-deploy/novabank.sqlite3` were not restarted or modified by Week8 work.

To stop the preview, first verify each listed process still has the expected workspace interpreter, Uvicorn module and port, then stop only those owned processes. Preserve the synthetic DB for reproducible review. Do not stop another service based only on a reused PID.

To roll back code, review the intended file-level diff against the preserved source snapshots and restore only the selected changes; do not bulk-reset this dirty shared worktree or remove user data. Use a new isolated DB/path for any older-version preview rather than opening the current DB with older schema assumptions. The D: runtime/model setup can remain inert; reverting app code does not require deleting existing Ollama models or environments.

Raw auth-bearing logs/databases remain local. Released screenshots mask secret input fields, Caido screenshots omit authorization headers, and published JSON contains redacted outcomes/source hashes. The previously rejected extra C attack-demo action was not retried to evade automatic review.
