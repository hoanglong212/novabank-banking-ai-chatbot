# Week8 integration and measured results

Updated 2026-11-15. The follow-up corrected seven application/evaluator issues, provisioned Qwen3, completed benign risk calibration, captured actual Caido boundaries and continuous MFA/QR demos, and refreshed localhost. **The supplied plan is not yet 100% accepted:** licensed Prompt Guard inference, the complete final-source evaluation matrix and the specified extra C attack-demo artifact remain incomplete. The user confirmed that original design/transcripts do not exist; the new [current-code design](../../thiet-ke-gateway.md) is a descriptive baseline, not fabricated historical evidence.

## Verified application changes

- Dashboard and assistant payment balances use the same bank data and all-payment-account scope. Requested card debt, savings principal and paid interest are rendered from successful bank reads, with field-specific minimization and final alias checks.
- Signed delegation, strict configurable policy, provenance, risk/cooling, source quarantine and bank-generated approval evidence remain separate enforcement layers. New-recipient policy conditions now receive bank-derived facts. Custom `deny_and_flag` actions halt and revoke regardless of rule naming; plain denial is not accidentally upgraded by its name.
- Failed upstream runs now record terminal risk history, clear bound request/vault and reject pending proposals. Missing detectors still deny and revoke, but no longer permanently quarantine benign sources or train attack-flag history from an availability failure.
- `get_bills` accepts a strict optional PAID/UNPAID status filter and still rejects caller-selected owner arguments. Qwen3 requests explicitly disable thinking during tool execution.
- New recipients require bound TOTP step-up and a distinct final email OTP. QR payment prose rejects URL/instruction content. Customer transfer-cap changes use bank approval/confirmation. Synthetic data contains 50 customers, 125 accounts and six months of reconciled activity.
- G2 evaluation now recognizes an exact foreign bank balance, with own-balance/wrong-amount controls. Runner v4 rejects older checkpoints. This fixes a scoring blind spot, not a demonstrated application leak.

## Final checks

| Check | Observed result | Evidence/scope |
|---|---|---|
| Backend full suite | **828 passed, 1 xfailed**, 353.24s | `.local/week8-completion/backend-final.log`, after all follow-up code fixes |
| Research suite | **38 passed**, 5.25s | Exact matching, denominators, checkpoints and guard evaluation |
| Browser full suite | **49 passed**, 12.2m | Actual full Playwright run after follow-up fixes; build included |
| Component checks | **20 groups passed** | Configured `test:components` command |
| Ruff / whitespace | Passed | Backend/app/tests, agent service, research and scripts; `git diff --check` |
| Independent follow-up | **20 passed**, 3.20s | [Audit](COMPLETION_AUDIT.md), no new concrete defect in reviewed changes |
| API matrix | 128 routes; 452 passed observations; 128 explicit N/A | [Original matrix](API_TESTS.md); included again in full backend suite |
| Actual Caido | 401 / 403 / 404 and two owner-positive 200 controls | [Screenshots and metadata](CAPTURE_COMPLETION.md); three representative cases, not all matrix observations |
| Continuous recordings | MFA, malicious QR rejection, genuine QR through **email OTP** | [Capture report](CAPTURE_COMPLETION.md); genuine QR makes no payment confirmation |
| Preview | Login/dashboard passed after restart | Synthetic-only ports 8081/8094; existing deployment 8080/8093 untouched |

The xfail intentionally retains the former anonymous-outbox exploit, now rejected. The backend warning comes from a deliberately short wrong JWT key in a negative test. Vite retains its existing bundle-size advisory. Earlier migrations 1–20, integrity and ledger reconciliation passed on copies; no schema changed in this follow-up. [Verification hashes](verification.json), [previous report](RESULTS_PREVIOUS.md) and [failures/corrections](../week8-evidence/FAILED_ATTEMPTS.md) preserve scope and history.

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
backend/.venv/Scripts/python.exe -m pytest research/tests -q
backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests agent_service research scripts
git diff --check
npm --prefix frontend run test:components
npm --prefix frontend run test:e2e
```

## Actual model and calibration evidence

T6 completed a registered 100-task corpus and 20-case supplement using actual Qwen2.5/D calls. Main utility was **90/100**: 91 measured tasks (one invalid bill argument) and nine detector-unavailable reads. The combined **100 legitimate proposals** matched their expected bands: 94 medium, six high; all three large/new-payee proposals had cooling. No thresholds were changed to improve the result. The source snapshot predates the bill/outage fixes; those measured failures remain recorded. The first quota-limited batch is also retained. [Full calibration report](T6_BENIGN_CALIBRATION.md).

T9 now covers both requested victim models. Qwen2.5 was **20/20 off and on**; newly provisioned Qwen3 was **18/20 off, 20/20 on**, with thinking disabled. Additional Llama3.2 compatibility was 15/20 each. There are 120 actual calls across the original and follow-up experiments. These are narrow field-reading tasks, not proof of general superiority. [Method and raw outputs](../week8-evidence/spotlighting/README.md).

T10 measured Qwen2.5 on 52 synthetic Vietnamese samples: 26 TP, 26 TN, precision/recall 1.0 on this small corpus. An isolated Torch/Transformers CPU runtime is now installed and dependency-checked, but **both Prompt Guard variants still have zero measured coverage** because licensed weights are absent. The user explicitly has not accepted Meta's license. [Readiness and preparation](MODEL_READINESS.md).

T11 retained two real serial Llama3.2 calls with valid isolated schemas and the earlier two timeouts. One card request was categorized ACCOUNT; schema validity is not semantic accuracy. [Successes](../week8-evidence/t11-live-recheck.json), [earlier attempts](t11-live-evidence.json).

The actual final-source **Qwen3/D positive demo** returned **80,770,000 VND**, matching the bank's two-account total. A model-generated 100,000 VND personal-cap proposal changed nothing before evaluator-simulated human approval and separate bank OTP; afterward a 100,001 VND draft was rejected and a 10,000 VND draft accepted. Four primary model calls returned HTTP 200. [Redacted evidence](../week8-evidence/live-positive-demo-qwen3.json). This is not an attack experiment or a claim that the accepted draft posted money.

## Research coverage and remaining gates

The historical realistic-data subset remains **336 observations: 137 eligible attacks, four benign controls, 192 unavailable, three errors**. Eligible strict L1/L2/L3 were zero; A/C each had only one completed adaptive N=10 case. B/D measured fixed replays but had no eligible adaptive source budget. Historical Qwen3 rows were unavailable before provisioning and are not retroactively converted to measurements. C did **not** establish the hypothesized L1 > 0 with L3 approximately zero. [Detailed original results](T12_REALISTIC_RESULTS.md).

A read-only supplementary v4 exact-foreign-balance check examined 80 retained G2 artifacts (60 measured, 20 unavailable), found no changed L1/L3 results, and preserved all originals. Another 80 unavailable G2 rows had no final artifact. This adds limited exact-fact coverage to retained outputs, not fresh inference or a full final-source benchmark. [Recheck](../week8-evidence/g2-exact-fact-recheck.json), [scoring definitions](T12_EVALUATION.md).

The final-source snapshot on D: contains a **plan only** for 7,600 observations, 113 cases and eight model/config cells: zero executed rows. Complete acceptance still requires:

1. Human license acceptance/access and local base/VI Prompt Guard weights, followed by actual detector comparison and healthy source-utility measurement.
2. The complete final-source two-model A–D/N=10 source/goal evaluation. Current QR parser/browser evidence is separate from the still-unsupported QR-to-agent ingestion channel.
3. The specified extra C attack-demo artifact. Automatic safety review rejected that action; it was not retried through another route.

Original mentor transcripts/design do not exist according to the user. The new technical baseline replaces the missing design for future implementation, while a historical controlled before/after replay cannot be certified. No universal absence-of-bugs or superiority claim is made.

Local preview: **http://127.0.0.1:8081**, agent service 8094, default configuration D, existing demo sign-in credentials and normal verification retained. [Evidence index](../week8-evidence/README.md), [task ledger](progress.md), [completion mapping and rollback](completion.md).
