# Week 8 security gate

**Status: CHƯA ĐẠT.** Acceptance requires independent evidence for DOC-SEC-01 through DOC-SEC-07, NEW-SEC-1/2 and harness A–J on the merged application. These live attack scenarios remain unexecuted in this verification.

| Evidence | Scope | Interpretation |
|---|---|---|
| Document RAG | Five ordinary document questions, three repetitions per configuration, real local models | Measures utility, citation grounding and passive marker checks on benign traffic. |
| Financial effects in D | Synthetic balances by account, approval counts by status and security event counts by event before and after benign document questions | A document question should leave balances and approvals unchanged. Security events can increase with normal auditing. |
| Benign utility | The 100 published prompts from `docs/release/week8-evidence/benign-calibration/calibration-100.json`, config D, four identical disposable 25-case cohorts per revision | The metric requires the expected tool to be allowed. Approval proposals can be created. Each cohort checks the financial snapshot. |
| Historical functional scripts | The remote branches and PR heads searched contained no original `positives.py` or `positives2.py` | The four replacement functional prompts have independent provenance. Historical equivalence remains unknown. |

The RAG observer checks the published synthetic marker in the displayed answer, tool JSON, complete SSE response, event rows and process logs on the benign fixture set. It stores a boolean per surface. The marker search and the D snapshots measure these specific inputs. The security verdict remains open until the required scenarios have independent results.

Run the benign comparison from the repository root with the project Python environment, local Ollama models and the licensed local Prompt Guard directory:

```powershell
python verify/benign_comparison.py --baseline 5f0a87a --candidate HEAD --guard-model models/prompt-guard-2-86m
```

The report for each source SHA records every case, cohort, metric and financial snapshot in `docs/release/week8/runs/<source-commit>/published-utility-D.json`. An initial single-cohort attempt on the baseline measured 34 successful tasks before the remaining 66 returned errors. The published comparison uses cohorts of 25, matching the original calibration procedure and keeping the production request quotas active.
