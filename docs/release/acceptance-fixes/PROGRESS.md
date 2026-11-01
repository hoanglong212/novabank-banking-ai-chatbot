# Acceptance fixes — 2026-11-01

Authority: user's four ordered groups and specification decisions in this conversation.
No demo DB writes, dependencies, commits, pushes or research reruns.
Original audit measurements remain historical evidence. Red probes moved from
`docs/release/acceptance-audit/test_requirements.py` into case-named backend tests.

1. TRF-14: 4 RED -> 4 GREEN. 30/user + 60/IP per 300s, failed lookups count;
   ASGI peer used, arbitrary forwarding headers ignored. Group 1: 228 pytest pass,
   13 expected unresolved/spec-decision probes fail; 15 component groups, 12 E2E pass;
   disposable E2E reconciliation balanced.
2. SEC-01: 6 RED -> 17 GREEN (includes route inventory and all forbidden role pairs).
   Support keeps own alerts: tested customer money-alert read/mark isolation and own
   security alerts. Research requires admin + RESEARCH_SANDBOX_ENABLED=true (default false).
   Group 2: 246 pytest pass, 6 remaining probes fail; components pass; 11 E2E pass,
   DSH-01 fails as expected, BEN-01 selector corrected from Accounts to Accounts & recipients,
   security E2E hit the shared test server login quota after adding logins (fixture isolation needed).
   Reconcile balanced. ADM-03 expectation updated by explicit user decision and passes.
3. BEN-01, ADM-02, PFM-02, STM-01, DSH-01: complete. Backend 28 tests pass including SEC-01.
   Additional PDF text check uses stdlib PDF stream decoding (pypdf is not installed).
   No dependency installed. Interbank test fixture corrected to supported Demo Bank A.
4. AI-02, AI-12, AI-11: complete. Each corresponding backend probe observed RED then GREEN.
   UI stop component observed RED then GREEN. E2E revealed history/live-text race, fixed in hook.
   Separate real Qwen HTTP acceptance passed with inline citations, text events, cancellation,
   unchanged balances and a pending (unexecuted) transfer proposal.

Final verification: 271 pytest pass, 17 component groups pass, 15 E2E pass,
reconcile balanced with no discrepancies. Financial coverage command repeats all 271 tests
and passes at 93.58% executed lines across the five configured financial modules.
Route matrix: 113 entries, including 104 API route/method pairs, docs and optional static mount.
Group 3 UI is complete: beneficiary edit/search and balance visibility/aggregation E2E pass.
The historical identity E2E's second Show click was changed to assert retained visibility;
financial expectations are unchanged. Final review: self-review; no independent review conducted.
No commits, installs, research experiment reruns, demo writes or demo restart.

Shared interfaces: recipient quota covers agent approval and legacy transfer preparation;
new beneficiary/cancel routes must be explicitly added to SEC-01's matrix;
posting budget notifications must remain inside atomic financial transactions;
statement totals derive from ledger postings, not mutable balance caches;
AI cancellation must reject late tool effects and late finish writes.

Decisions: AUTH-03 rejects extra role/balance with 422; ADM-03 locks draft fee but
rechecks current limits at confirm; AI-13 accepts 401/403 with no effects;
NF-07 preserves en-US money formatting. Operations cannot freeze accounts;
auditor cannot read customer ticket content. Research AI-14/PI-05/PI-06 deferred by user.
