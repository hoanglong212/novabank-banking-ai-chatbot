# Week8 integration and measured results

The integrated application and evidence package are available locally. **The entire T0–T13/C1–C7 plan is not yet fully accepted:** the original design and incident transcripts, licensed Prompt Guard models/runtime, requested Qwen3 model, full evaluation matrix and specified capture artifacts are still missing. Passing application tests does not replace those gates.

## Application changes

- Dashboard and assistant payment balances share bank data and the same all-payment-account scope. Requested card debt, savings principal and savings interest are rendered from successful bank tool reads, including actual paid interest on closed deposits. A model's invented amount is never used as the current bank balance.
- Field-specific minimization suppresses unrequested financial data and foreign full account identifiers. Restored aliases are checked at the final bank boundary and are not expanded a second time afterward.
- Signed delegated authority, strict configurable policy, provenance, risk/cooling, source quarantine and bank-generated approval evidence form separate enforcement layers. The model cannot post a payment or create an identity directly.
- New recipients require request/session/factor-bound TOTP step-up and a separate final email OTP. QR payment prose rejects URL/instruction content and displays its source and recipient warnings.
- A new customer transfer-limit proposal uses the same approval/verification boundary. A reproducible synthetic seed supplies 50 customers, 125 accounts, staff in each role and six months of reconciled activity.

See [design/source map](DESIGN_STATUS.md), [threat model](../THREAT_MODEL.md), [RBAC matrix](../RBAC_MATRIX.md), [scoped independent review](INDEPENDENT_REVIEW.md) and [task ledger](progress.md).

## Verification

| Check | Observed result | Scope |
|---|---|---|
| Final backend full suite | 818 passed, 1 xfailed in 338.79s | `.local/week8/backend-final.log`; includes the final paid-interest correction |
| Final financial regressions | 35 passed in 10.70s | Balance consistency, privacy/minimization, product routing; actual action/OTP positive controls |
| Research suite | 36 passed in 3.92s | Matching, denominators, fixed/adaptive CLI control, checkpoint recovery, source fixtures and guard evaluation |
| Browser full suite | 49 passed in 12.7 minutes | Actual Playwright run, `.local/week8/e2e-release.log`; before the final backend-only interest-field correction |
| Component checks | 20 groups passed | Actual configured `test:components` command |
| Frontend build | TypeScript and Vite passed | Existing >500 kB bundle advisory remains |
| Ruff and whitespace | Passed | Backend/app/tests, agent service, research, scripts; `git diff --check` |
| API coverage | 128 routes, 452 passed observations, 128 explicit N/A | No failures, unobserved routes or matrix drift; [API_TESTS.md](API_TESTS.md) |
| Migration copies | Versions 1–20, integrity and reconciliation passed | Source hashes unchanged; [report](../week8-evidence/migration-check.json) |
| Local preview | Login and dashboard passed after final app correction | Synthetic DB, [screenshot](../week8-evidence/local-preview-dashboard.png) |

The xfail is the intentionally retained former anonymous-outbox exploit, now rejected. The warning in the backend suite is from a deliberately short wrong JWT key in a negative test. Neither is reported as an unfixed application defect. Earlier failures and corrections are retained in [FAILED_ATTEMPTS.md](../week8-evidence/FAILED_ATTEMPTS.md).

Reproduction from the repository root (PowerShell, existing environment):

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
backend/.venv/Scripts/python.exe -m pytest research/tests -q
backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests agent_service research scripts
git diff --check
npm --prefix frontend run test:components
npm --prefix frontend run build
npm --prefix frontend run test:e2e
backend/.venv/Scripts/python.exe scripts/check-migrations.py
```

The browser fixtures and migration command use isolated databases. No Week8 operation migrated or restarted the existing deployment at port 8080 or wrote its `.local/local-deploy/novabank.sqlite3` database.

## Live measurements

T9 made 80 actual calls: 20 tasks per model with marking off and on. Qwen2.5 achieved 20/20 in both conditions; Llama3.2 achieved 15/20 in both. This is narrow field-reading utility, not a general quality or security benchmark. [Raw evidence and method](../week8-evidence/spotlighting/README.md).

T10 measured Qwen2.5 on 52 synthetic Vietnamese examples: 26 true positives, 26 true negatives, precision/recall 1.0. Both Prompt Guard variants have zero measured coverage because the required runtime and licensed weights are absent; their precision/recall is unavailable. The small templated corpus does not establish robustness. [Detector report](../week8-evidence/t10-qwen-actual.json).

T11's two serial local Llama3.2 calls produced valid isolated schemas; the earlier two timeouts remain recorded. Schema validity is not semantic accuracy: one category was ACCOUNT for a card-related request. [Successful serial calls](../week8-evidence/t11-live-recheck.json), [earlier failures](t11-live-evidence.json).

The initial C/Qwen2.5 N=2 smoke measured 18 attack attempts and one benign control; strict L1/L2/L3 were zero. The measured observations **do not establish C having L1 > 0**. [Smoke results and limits](T12_SMOKE_RESULTS.md).

The realistic-data N=10 subset finished with **336 recorded observations**: one adaptive transfer-memo/G2 case, three fixed synthetic mentor-goal replays and two benign controls for each configuration/model. Of these, 137 attack attempts and 4 benign controls were eligible real-model measurements; 192 observations were unavailable and 3 had generator errors. No excluded row recorded an L3 effect.

| Configuration / model | Eligible attacks | L1 | L3 | Utility under attack | Benign utility | Excluded observations |
|---|---:|---:|---:|---:|---:|---|
| A / Qwen2.5:7b | 39 | 0/39 | 0/39 | 20/39 | 2/2 | 1 error |
| B / Qwen2.5:7b | 30 | 0/30 | 0/30 | 20/30 | Unavailable | 12 unavailable |
| C / Qwen2.5:7b | 38 | 0/38 | 0/38 | 30/38 | 2/2 | 2 errors |
| D / Qwen2.5:7b | 30 | 0/30 | 0/30 | 20/30 | Unavailable | 12 unavailable |
| A, B, C, D / Qwen3:8b | 0 | Unavailable | Unavailable | Unavailable | Unavailable | 42 per configuration; model absent |

L2 was also zero in all eligible attempts. A and C each completed **one genuinely adaptive N=10 case**, with ASR after 1 and after 10 both 0/1. B and D had no eligible adaptive budget because the required source detector was unavailable; their 30 measured attacks each were fixed mentor replays. Fixed replays remain in the L1/L2/L3 table but are excluded from adaptive ASR. Three malformed outputs came from unused adaptive-generator calls before fixed replays in runner v2; runner v3 fixes that scheduling bug, and the original failures remain in the report.

**Answer to the C hypothesis: no, this subset does not establish L1 > 0 with L3 approximately zero.** C observed L1=0/38 and L3=0/38. Counting quoted attack text as successful model compromise would produce a false positive. Zero observed effects do not establish superiority over A/B/D or security against untested attacks.

The benchmark's immutable application snapshot predates the final generic-debt and paid-interest corrections in `agent/disclosure.py` and `agent_output.py`. It is not a full evaluation of the final application or every required source/goal combination. [Detailed channel/model results](T12_REALISTIC_RESULTS.md), [CSV](t12-realistic-results.csv), [summary](t12-realistic-summary.json) and [source/model metadata](t12-realistic-metadata.json) retain that distinction. Raw observations and the original pre-correction summary remain in the local experiment directory.

The measured model was Qwen2.5:7b digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, Ollama 0.40.16. Reproduce the selected matrix with the corrected current runner in a **new** output directory:

```powershell
backend/.venv/Scripts/python.exe scripts/week8_evaluate.py --project-root .local/week8/frozen-final --out .local/week8-evaluation/realistic-rerun --execute --models qwen2.5:7b qwen3:8b --configs C A B D --channels transfer_memo --goals G2 --attempts 10 --benign-controls 2 --seed-db .local/week8/realistic/bank.sqlite3
backend/.venv/Scripts/python.exe scripts/week8_report.py .local/week8/frozen-final/.local/week8-evaluation/realistic-rerun
```

Use `--project-root .` and another new output directory to measure the current final application. Runner v3 rejects the old v2 checkpoint rather than mixing execution semantics. The selected seed needs its adjacent synthetic `.manifest.json`; the prepared local seed has it. No command pulls a missing model or accepts a license.

For exact scoring definitions, source-access assumptions, fixed mentor replays, adaptive denominators and unsupported QR-to-model coverage, see [T12_EVALUATION.md](T12_EVALUATION.md). An observed zero on a finite corpus is not proof of no vulnerabilities.

## Local demo and evidence

Updated synthetic preview: **http://127.0.0.1:8081**, paired agent service on port 8094. The default gateway configuration is D. Existing demo sign-in credentials are preserved; the app still requires its normal login verification. The preview uses the reconciled synthetic dataset, not the user's existing deployment data.

An actual final-source Qwen2.5/D demo on a disposable copy of that dataset passed: assistant balance **80,770,000 VND** matched the dashboard's two-account total; a model-generated 100,000 VND personal transfer-limit proposal changed nothing before evaluator-simulated human approval and bank OTP confirmation; after confirmation a 100,001 VND draft was rejected and a 10,000 VND draft was accepted. Four captured primary model calls returned HTTP 200. [Redacted demo evidence](../week8-evidence/live-positive-demo.json), [verification/source hashes](verification.json). This is a legitimate end-to-end flow, not an attack-ASR measurement or a claim that the draft posted money.

The [evidence index](../week8-evidence/README.md) links the five-layer HTML/PDF slide, API results, approval screenshots, MFA/quishing GIFs and failures. The GIFs are slideshows of actual test screenshots, not continuous screen recordings. No Caido capture or native PowerPoint artifact is claimed.

## Remaining acceptance dependencies

1. Supply the original `thiet-ke-gateway.md` and original mentor transcripts to reconcile the exact 72 steps, source list, A–D choices and historical replay. The supplied archive was inspected; these materials were not found.
2. A human must accept the Prompt Guard license and provision the base/VI weights and runtime. The plan explicitly reserves that step to a human. The existing adapter fails closed when unavailable; this reduces benign utility and is not a pass for a deployed classifier.
3. Provision the requested Qwen3:8b model, then run the full four-configuration, two-model, source/goal N=10 matrix and broader benign calibration. No model was silently downloaded or substituted. Risk thresholds remain provisional; a 100-task benign calibration is not claimed.
4. Establish and measure an actual QR-to-agent context path before claiming that channel's model-ingestion ASR. Existing QR parser/browser controls are separately verified.
5. Capture the requested Caido examples and continuous demo artifacts if those exact deliverables are required. Original-incident before/after measurements cannot be reconstructed from synthetic substitutes.

The delegated extra C-configuration attack-demo action was rejected by automatic safety review for possible cybersecurity risk. It produced no C attack GIF, and was not retried through a different route to evade that review. Existing authorized test results remain in this package.

No claim of universal bug freedom, production banking readiness, or superiority over other systems is made.
