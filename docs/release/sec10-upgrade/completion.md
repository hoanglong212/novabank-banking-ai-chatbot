# SEC-10 completion evidence

Scope authorized by the user: upgrade certifi, pip, Vite and postcss-selector-parser; add pip-audit as a development tool; verify and commit the current Security / AI / Lab changes locally, without pushing or migrating/restarting the demo. Detailed Vietnamese report: [REPORT_VI.md](REPORT_VI.md).

| Acceptance criterion | Evidence and result |
|---|---|
| Fix advisories without weakening SEC-10 | Original probe failed before upgrades; unchanged probe passes in the 359-test suite. [Before](SEC-10-before.txt), [pytest](pytest-output.txt). |
| Upgrade only the four approved existing packages | Full before/after installed Python inventory and npm lock comparison; [package-changes.json](package-changes.json). pip-audit 2.10.1 adds its required 15 dependencies. |
| Real scanners, no ignored advisories or skipped Python packages | Strict pip-audit covers all 110 installed Python distributions; npm audit covers the lockfile. Both exit 0 and report zero vulnerabilities. [Python](pip-audit.json), [Node](npm-audit.json). |
| Run configured checks | Pytest 359 pass; financial line coverage 93.58% with another 359 passing tests; 17 component groups; TypeScript/Vite build and 16 E2E pass; compileall and pip check pass. [Exact commands and exit codes](verification.json). |
| Reconcile without touching demo DB | Validated E2E DB path is under `.local/e2e`; ledger total 0, balanced, no mismatches or unbalanced journals. [Reconcile](reconcile.json). |
| Preserve meaningful test expectations | Initial coverage failure traced to wall-clock rollover splitting the TRF-14 request quota into 20/41 requests. Test-local clock fixture fixes nondeterminism; no assertion or production change. Failed attempt preserved privately and explained in the report. |
| Retain previous round's case evidence | [Security / AI / Lab case table](../security-ai-evidence/REPORT_VI.md); only its historical SEC-10 status is superseded by this upgrade. |

Changed files this follow-up: `backend/requirements.txt`, `backend/requirements-dev.txt`, `frontend/package.json`, `frontend/package-lock.json`, test-local fixture in `backend/tests/test_TRF_14.py`, current audit evidence and this report directory. The same local commit includes the previously authorized Security / AI / Lab production fixes and regression tests documented in the prior report.

Review: Codex self-review of code, dependency scope, tests, evidence and Git candidates. No independent reviewer was used. No repository `engineering.json` is configured; actual repository checks were run directly. Checks ran on Windows/Python 3.14, not the Ubuntu/Python 3.12 CI runner. No push, so remote CI is not claimed.

Demo backend remains on its existing schema/code until a separately authorized migration/restart. E2E rebuilds the existing frontend distribution. No new real-model research was run. M6, NF-08, AI-14 and PI-05/06 remain deferred as requested. Audit results reflect known advisories at scan time, not universal security certification.

Rollback: inspect the local commit and apply selected reverse patches if authorized. Previous manifests, inventories and the two old Node package directories are preserved under `.local/sec10-upgrade/before`. Do not reset the workspace or restore over the running demo database. Reinstalling older vulnerable packages would reopen SEC-10.
