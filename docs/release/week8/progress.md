# Execution ledger — docs/ke-hoach-agent-build-week8.md

User authorization (2026-11-15): execute the whole T0–T13/C1–C7 plan continuously, settle routine questions through research and engineering judgment, improve where justified. No completion claim until measured evidence exists. User replaced the previous full-app audit; its Playwright run was deliberately stopped after 32 passing tests. Its logs and new regression tests remain preserved.

## Workspace and process

- Working tree: original project, feature branch `week8/t1-security-events`, based on existing `week7/fix-outbox-profile-gateway` at `6a6617e`; not the plan's historic `314a4b6` base.
- Existing uncommitted balance fixes, audit tests and user documents are preserved. Do not reset/stash/overwrite them.
- No writes to `.local/local-deploy/novabank.sqlite3` or restart of that deployed instance for week8. All migrations/model runs use separate databases.
- Use existing `backend/.venv/Scripts/python.exe` and `frontend/node_modules`. Do not auto-install dependencies/services.
- No remote push, merge or publication. Local branch/reviewable artifacts first.
- Required flow: finding → red regression + positive control → fix → green → evidence.

## Rulings

1. Supplied plan is the approved scope; user opted out of clarification. No repeated design approval gate. Implement sequentially with `msi-aef-executing-plans`; file ownership rules remain binding.
2. Missing original `thiet-ke-gateway.md`: searched repository, Downloads DOCX texts, connected Drive and private Pages. The 72-step design and exact A–D matrix were not found. Do not invent their contents or claim a 72-step reconciliation. Implement requirements explicitly present in the supplied plan; record provisional engineering choices separately. The user subsequently confirmed those originals do not exist. The new docs/thiet-ke-gateway.md is the descriptive current-code baseline; historical replay remains unavailable, not an indefinite file-recovery task.
3. T10 external prerequisite: no Torch/Transformers in backend venv, no cached Prompt Guard 2 model found. Plan explicitly says a human accepts Meta's license/downloads model, not agent. In the follow-up, an isolated CPU runtime was installed and checked on D:, but the user confirmed no license acceptance, so weights/inference remain unavailable. Build local-only adapter and fail-closed tests; real detector precision/recall cannot be fabricated. No license acceptance or automatic download.
4. Historical starting state: Qwen3:8b was not among existing Ollama manifests. Follow-up user-authorized provisioning succeeded; the exact Q4_K_M model now has 40 T9 calls and a four-call D positive demo. Original unavailable measurements remain unchanged. Existing models: Qwen2.5:7b, Llama3.1:8b, Llama3.2:3b, Mistral, nomic-embed-text. Preserve exact requested-model result as unavailable unless provisioned; an additional existing-model comparison must be labeled a substitution, not Qwen3 evidence.
5. Retain staff approval proposals and isolate ticket reading (T11 recommendation accepted under user's delegated judgment). Raw ticket text stays accessible to authorized humans in the existing UI.
6. Cooling-off and risk thresholds will be configurable, conservative initial research choices, tuned only against real measured benign utility. No claim these thresholds are banking standards.
7. C6 candidate functionality: customer transfer-limit change via explicit typed proposal, human approval, current-password/step-up, bounded by bank limits. Select final interface after inspecting current settings/schema; do not create a money execution capability in agent tools.
8. Research objective is a hypothesis, not a required fabricated outcome. Report whether C has L1>0 and L3≈0, even if the answer is no. Distinguish measured zero from missing/unavailable runs.
9. Ruling (follow-up request): the user's explicit request to complete the listed missing pieces authorizes provisioning Qwen3 and an isolated optional measurement runtime, superseding the prior no-automatic-install default for these named prerequisites only. Keep the existing backend environment and deployment intact; use D: for large lab artifacts because C: has limited free space. Meta license acceptance and gated access still belong to the user; the user explicitly confirmed the license is not accepted. The user also completed the Caido privacy choice personally, after which actual isolated capture succeeded. Do not invent source documents or retry the previously rejected extra C attack-demo action.

## Evidence already collected on starting code

In `.local/full-app-audit-20261115/`: backend **685 passed / 1 xfailed**, research **15 passed**, component **19 groups passed**, build passes, Ruff passes (backend/app agent_service scripts backend/tests). Real two-process Qwen balance/RAG/transfer-proposal/cancel acceptance passed (`real-agent-report.json`). Migration copies passed. Live DB read-only integrity/reconciliation passed. Full E2E interrupted by user's explicit direction after 32 passing tests; not a full-suite pass.

Prior-audit credit-timezone defect fixed after watched red; monthly credit queries now use Vietnam calendar dates. Three new dashboard E2E audit tests were added but not executed before task replacement. They are outstanding baseline findings, not week8 regressions introduced by new source changes.

## Task state

| Task | State | Evidence / remaining |
|---|---|---|
| T0 | Current baseline documented; historical evidence unavailable | User confirms original design/transcripts do not exist. New descriptive design and synthetic mentor controls are explicit; no fabricated historical replay |
| T1 | Implemented; integration verified | Migration12, transaction-local emit/redaction/dedup/ladder, raw-filtered evidence, approval/OTP/posting correlation; included in passing full backend suite |
| T2 | Implemented; integration verified | Watched memo ALLOW red; added status tool screening; focused and full backend suites passed |
| T3 | Implemented; integration verified | Migration13, monotone labels/history, critical argument origins; focused and full backend suites passed |
| T4 | Implemented; integration verified | Required signed tools/intent/role; tamper tests; focused and full backend suites passed |
| T5 | Implemented; independently rechecked | Strict JSON A–D, expiring sessions and default-D confinement; recipient_new fact and custom deny_and_flag semantics corrected |
| T6 | Implemented; 100-proposal calibration measured | Main 100 requests + 20 supplement; 100 proposal bands match. Main utility 90/100, nine detector outages and one invalid argument preserved. Subsequent bill/outage corrections tested separately |
| T7 | Implemented; integration verified | Bank templates, field origins/risk/new recipient, contextual OTP; 20 component groups and full 49-case browser suite passed; actual approval capture retained |
| T8 | Implemented; integration verified | Persistent source quarantine, atomic halt/revoke/reject/notify, support-only release; focused and full backend suites passed |
| T9 | Implemented; requested models measured | Qwen2.5 off/on 20/20; Qwen3 off 18/20, on 20/20 with thinking disabled; additional Llama 15/20 each. 120 actual calls total |
| T10 | Adapter/runtime ready; comparison incomplete | Qwen 52/52 synthetic samples measured. User has not accepted Meta license; base/VI licensed weights and real inference absent |
| T11 | Implemented; narrow live schema check | Main-model enum boundary; encrypted human-only summary rendered in staff trace; 2 serial live isolation calls returned valid schemas, earlier timeouts preserved; not a semantic-accuracy benchmark |
| T12 | Runner v4 ready; full measurement incomplete | Historical 336 observations retained; exact-foreign-fact matcher fixed and 80 retained G2 artifacts rechecked. Qwen3 now available;7,600-row final-source plan has zero executed observations; unsupported QR-to-agent path remains explicit |
| T13 | Current design/evidence documented; one artifact unavailable | New design baseline, scoped independent audit, RESULTS and completion mapping. Specified extra C attack GIF rejected by automatic safety review |
| C1 | Implemented; integration verified | Env flag cannot enable legacy outside active pytest; test server actually hosted in pytest; mentor controls use fresh grants after revocation; full suites passed |
| C2 | Implemented; final regression verified | Nested alias, unsolicited card/generic debt and actual paid-interest field fixed. Requested payment/card/savings amounts use bank templates; 35 focused tests passed, 31 independently rerun before final root follow-ups |
| C3 | Implemented; continuous positive/negative captures verified | Actual malicious QR rejection plus genuine QR→new-payee TOTP→separate email OTP recording; no payment confirmation in the latter |
| C4 | Implemented; continuous MFA capture verified | Real TOTP login→new-recipient step-up→distinct email OTP→receipt; secrets masked, independent capture assertions passed |
| C5 | Matrix and representative Caido evidence measured | 128 routes, 452 passed observations, 128 explicit N/A; actual Caido 401/403/404 with 2 owner-positive 200 controls and screenshots |
| C6 | Seed/functionality verified; full T12 rerun incomplete | 50 customers / 125 accounts, 6 months reconciled data; Qwen2.5 and Qwen3/D positive balance/cap demos; full matrix remains separate |
| C7 | Package expanded; complete research acceptance pending | Continuous MFA/QR WebM/GIF, actual Caido, HTML/PDF slide, calibration and real-model demos. Original incidents absent; full matrix and rejected C artifact unavailable |

## Research sources consulted

- Google Research, CaMeL: https://github.com/google-research/camel-prompt-injection — provenance/capability separation; inspiration, not proof NovaBank is secure.
- Microsoft MSRC, 2025-07-29: https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks — layered probabilistic/deterministic defenses and spotlighting.
- Meta Prompt Guard 2 model card/license: https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M — actual local-model prerequisite and classification interface.

Final command outcomes, realistic-data measurement and remaining acceptance gates are consolidated in [RESULTS.md](RESULTS.md). T10/T12 still require licensed models and full measurements; historical materials are confirmed nonexistent. Caido/continuous artifacts and calibration have actual evidence. Implementation and plan-only manifests are not measured success.
