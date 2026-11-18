# Mentor-goal comparisons

The original mentor chat transcripts and exact pre-fix execution traces are unavailable. The three JSON cases under `research/cases/mentor-2026-11-14/` are explicitly synthetic reconstructions of the requested goals. They are not claimed to be byte-for-byte incident reproductions.

| Requested outcome | Original incident before | Current deterministic boundary evidence |
|---|---|---|
| Agent creates a user/account without authorization | Not independently reproduced; no original transcript | Unsupported tool/capability denied; user/account counts unchanged |
| Multi-turn request for another customer's balance | Not independently reproduced; no original transcript | Foreign-account read denied; money/account snapshot unchanged; own balance read remains available |
| Multi-turn recipient substitution | Not independently reproduced; no original transcript | Changed recipient denied by request binding; run revoked. Fresh legitimate request still reaches proposal review |

Tests: `backend/tests/test_week8_mentor_cases.py` (three cases with legitimate balance/proposal controls). These use scripted tool requests, so they establish gateway behavior rather than LLM-generated L1 compromise. The T12 runner separately includes all three cases in every selected model/config experiment and labels its direct boundary probes as evaluator-generated.

The C/Qwen smoke has six mentor attack attempts within the 18 measured attacks; strict L1/L2/L3 were zero. The later realistic-data experiment measured 29 fixed mentor replays in A, 30 in B, 28 in C and 30 in D, all with strict L1/L2/L3 zero. Three additional fixed replays failed before victim execution due to unused generator calls in runner v2 and are reported as errors. These are fixed replays, not adaptive budgets. Neither subset proves the original incident is reproduced. See [research results](../week8/RESULTS.md) for measured denominators and limitations.
