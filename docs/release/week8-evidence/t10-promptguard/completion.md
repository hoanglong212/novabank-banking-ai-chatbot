# T10 follow-up completion evidence

Branch: `week8/t10-promptguard-run`, base `week8/integration` / `b5145ac`.
Scope and measured limitations: [T10 results](../../week8/T10_PROMPTGUARD_RESULTS.md).

| Requested acceptance | Actual evidence |
|---|---|
| Both local models on CPU, no download/token use | [CPU probes](cpu-readiness.json), local-only safetensors loader with token=False, offline benchmark env |
| Weights stay local; attribution supplied | models/ and .local/ ignored/untracked; repository NOTICE; preflight found no tracked forbidden path, credential-shape hit or file >10 MiB |
| Configurable path/threshold; missing model fail closed | backend/tests/test_promptguard.py; real local tests; environment-only per-process utility setup |
| Regex → PG2 → Qwen; classifier_signal; B/D versus A/C | backend/tests/test_source_chain.py and test_promptguard_signals.py, with actual bank API/event queries |
| Three detectors, calibration/held-out, language metrics | [Comparison JSON](detector-comparison.json): 168 primary rows, 84/84 split; unchanged damaged 52-row corpus separately retained |
| Repeat 100 benign D tasks and report false blocks | [Utility JSON](benign-utility-100.json): 97/100, 3 PG false blocks / 10 screened tasks, zero unavailable, 197 primary model calls |
| Preserve financial effects boundary | Four independent disposable databases, unchanged account/balance/card/completed-transfer snapshots; no approval/confirmation requests |
| Do not run B/D attack matrix | Only standalone detector classification and benign D tasks executed; R1 prerequisite remains |
| Checks and independent review | Commands below; reviewer /root/t10_promptguard_review found no remaining P1/P2/P3 |

## Actual checks

All commands ran on this branch; none of these counts are historical carryovers.

| Command | Result |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` | exit 0; 847 passed, 2 skipped, 1 xfailed; 405.25 s; one existing short-test-HMAC-key warning |
| `backend/.venv/Scripts/python.exe -m pytest research/tests -q` | exit 0; 42 passed; 4.40 s |
| `backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests agent_service research scripts` | exit 0; all checks passed |
| `D:/NovaBank-Week8-Lab/runtime/Scripts/python.exe -m pytest backend/tests/test_promptguard_local.py backend/tests/test_promptguard_signals.py -q` | exit 0; 6 passed; 8.65 s; both actual model folders configured |
| `git diff --check` | exit 0 |
| `scripts/week8-promptguard-benchmark.py` with the runtime/args in the results report | exit 0; all 660 primary-plus-legacy detector predictions available |
| `scripts/week8-promptguard-utility.py` with the runtime/args in the results report | exit 0; all 100 cases measured; utility failures retained |

The two normal-suite skips are the separately executed weight-dependent tests.
Real-model tests use `PROMPT_GUARD_TEST_BASE` and `PROMPT_GUARD_TEST_VI` with
resolved local folders, `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`,
and `OMP_NUM_THREADS=MKL_NUM_THREADS=4`. CI need not obtain licensed weights.
No new dependency or service was installed. `engineering.json` is absent, so
checks use actual repository commands. Frontend/E2E were not rerun locally for
this backend/research change; the repository's existing GitHub workflow handles
its configured checks. CI results are tracked on the PR; local pass is not CI pass.

## Review, limitations and rollback

The independent reviewer read all changed production/config files, tests,
research modules, scripts, release documents and JSON evidence. They recomputed
the corpus/split, hashes, all detector confusion counts/latencies, and exact
historical case identity; compared public utility rows with raw results. One
NOTICE-link typo was corrected. Inference and suites were run by the implementer,
not independently repeated by the reviewer. Final completion text/check-count
metadata was added after that review and is independently identified as such.

Source hashes are supplied because measurements preceded the final documentation
commit. App source remained unchanged throughout the utility run. Its recorded
base commit alone does not identify the changed app; use the included hashes.
Private raw model/API logs remain under ignored `.local/`, with hashes in the
public reports. Neither weights, databases, live credentials nor raw tokens are
published.

Limitations include reconstructed VI data, repeated templates, unknown training
overlap, mismatched English-negative source context, small language denominators,
and a lab threshold with 30% false blocks among screened benign sources. The
97-versus-90 before/after also includes intervening app changes. No production
robustness, B/D attack ASR, or VI application utility is claimed. The previously
reported account-target-binding P1 inherited from the base remains outside T10.

Rollback: close the unmerged PR or revert its commit; remove only this lab's
process-level Prompt Guard settings. No database migration, live-service update,
model download or credential change needs reversal. Do not delete user weights.
