# C5 API matrix verification

The added TestClient suite completed **9 tests in 13.82 seconds** against the parent integrated application source. It generated **580 applicability/probe observations** across **128 route-matrix entries**: **452 actual passed checks**, **128 explicit N/A**, **0 failed observations**, **0 unobserved routes**, and no route-matrix drift.

The actual passing checks include 107 anonymous rejections, 236 forbidden-role pairs, 31 cross-owner existing-resource requests, 4 body-bound ownership probes, 3 explicit query-owned resource probes, 9 implicit-identity collection checks, 9 owner-positive controls, 42 invalid-DTO checks, 6 otherwise-valid oversize/strict-type checks, 4 ordinary-JWT-on-delegated-route denials, and one monetary replay invariant. These are checks inside the nine test functions, not 452 separate pytest test cases.

## Reproduction

After integrating the files into the application checkout:

```powershell
$env:W8_API_EVIDENCE = '.local/week8-api/observations.jsonl'
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_week8_api_matrix.py -q --tb=short
backend/.venv/Scripts/python.exe scripts/week8-api-report.py --project-root . --evidence .local/week8-api/observations.jsonl --out docs/release/week8
```

For this isolated authoring worktree the actual command selected the parent backend package explicitly:

```powershell
<parent>/backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini -o pythonpath=<parent>/backend --import-mode=importlib backend/tests/test_week8_api_matrix.py -q --tb=short
```

`API_TESTS.md` is the route-by-case table; `api-observations.json` contains redacted observed statuses and concrete synthetic resource paths; `api-summary.json` records aggregate counts and runtime source; `api-http-examples.http` gives redacted TestClient request equivalents. Caido was not installed or used, and no proxy screenshot is claimed.

## Meaningful controls and setup corrections

Fixtures create real owned objects through normal routes: recipients, completed/pending transfers, tickets, attachment, savings goal, action challenge, agent run and approval. Authentication uses real local email MFA. The owned transfer/receipt uses real authenticator enrollment, new-payee TOTP step-up and the separate final email OTP. No factor is disabled to make the authorization test pass. Account balances remain reconciled by the shared fixture teardown.

The initial setup assumed the pre-C4 transfer flow and failed because new-payee step-up is now required; the fixture was corrected to perform it. A foreign-action probe initially omitted `Idempotency-Key` and reached the intended header check instead of ownership; a valid key was added before counting it as an ownership probe. These setup failures are not reported as application vulnerabilities. No new app vulnerability was found in the final cases.

N/A remains explicit for public/static/login-challenge routes, global role-protected resources, shared approved knowledge, absent JSON DTOs, and identity-derived routes without an owner selector. The suite does not invent IDOR tests on nonexistent resources or treat 422 validation failures as authorization evidence. It does not claim full per-route replay/concurrency coverage; existing session/MFA/product tests remain relevant.

## Completion mapping and limits

- Anonymous access and wrong-role pairs: actual HTTP 401/403, not invalid-body 422.
- Wrong owner: actual Alice-owned IDs, valid request types and Bob's credentials; 403/404 or the explicit financial `ACCOUNT_NOT_OWNED` domain refusal. Owner positive controls prove the records exist.
- Delegation: normal banking JWT refused; Bob delegation stays bound to Bob run and cannot read Alice balance; Bob own-balance positive control succeeds.
- Replay: same idempotency key returns original receipt, a different key is rejected, and balances do not change again.
- Types/bounds: 422 for typed JSON body violations, plus six otherwise-valid targeted boundary probes.
- Reports: route matrix digest and explicit unobserved-route detection prevent silently claiming coverage after route additions.

Changed files are only the new test, report exporter and documentation/evidence. No application source was edited. Ruff and `git diff --check` passed. This is implementer verification, not an independent security certification; the parent full-suite/reviewer/browser gates remain separate. To roll back, remove these added task files; no schema or database rollback is needed.
