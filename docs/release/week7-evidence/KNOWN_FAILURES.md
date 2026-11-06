# Failures observed during real-model evaluation

The full Qwen run `.local/week7-live/run-59e7c91d44` started before the savings trace correction and retains that original in-memory backend throughout its run. Do not describe its results as a clean post-fix evaluation.

## Numeric keys in savings traces

`get_savings` returns an interest-rate mapping with integer term keys. The trace sanitizer called `k.lower()` on dictionary keys, causing `AttributeError: 'int' object has no attribute 'lower'`. The delegated HTTP call failed and the agent recorded `UPSTREAM_ERROR`. Real Qwen exposed this because it selected `get_savings` for some savings-policy prompts; earlier mock tests did not cover the returned rate map through the delegated trace path.

The fix uses `str(k).lower()` for secret-key filtering while preserving the original key/value mapping. Three regression tests failed before the change and passed after it: baseline tool call, defended tool call, and nested numeric-key/secret filtering. Logs: `.local/week7-savings-red.log`; tests: `backend/tests/test_week7.py`.

The corrected application runs at port 8081 with agent port 8094. The previous 8080 instance and the full evaluation servers were not stopped or silently patched. Fresh browser/tool evidence for the new instance is in `media/browser-check.json`; check its origin and `get_savings` result.

## Model round limit

At least one completed observation reached `ROUND_LIMIT`, separate from the savings defect. The runner records it as an execution failure, not an attack blocked or a utility success. The final count is in `results.csv` and `summary.json`. This behavior has not been eliminated by the trace fix.

## Post-fix rerun — 2026-11-06

The full run completed 2,070 observations with 96 execution failures: 90 `UPSTREAM_ERROR`, one `ROUND_LIMIT`, and five `ANOMALOUS_SEQUENCE`. A fresh isolated backend then reran all 15 affected scenario IDs across baseline/defended, five repetitions each (150 observations).

For the exact 150 matched trials, failures decreased from 96 to 6. `UPSTREAM_ERROR` decreased from 90 to zero; the remaining counts stayed at one `ROUND_LIMIT` and five `ANOMALOUS_SEQUENCE`. Tool/argument utility successes increased from 40/150 to 90/150. These selected cases do not provide an unbiased new full-suite utility estimate. The unchanged full run remains the primary measured dataset; see [the paired comparison](postfix-regression/comparison.md) and raw before/after run directories in its JSON.

The round-limit case repeatedly read beneficiaries/accounts/transactions without reaching the expected transfer proposal. The anomalous-sequence case repeated `get_bills` with unsupported `status: unpaid`; the schema takes no arguments and rejected both attempts. The model did not recover before the existing sequence guard stopped it. This is a legitimate-task failure, not a successful attack. No guard, schema or tool budget was relaxed to make the benchmark pass.

## New conversation selection race

A delayed initial history response could override the user's New conversation action. A selection-generation check now prevents the stale response from changing that choice. The browser regression failed before the fix and passed after it. Logs: `.local/week7-history-race-red.log`, `.local/week7-history-race-green.log`.

Execution errors are excluded from the reported rate denominators, so rates are conditional on completed observations. Always disclose the error and exclusion counts; do not present zero observed ASR as a reliability or security guarantee.
