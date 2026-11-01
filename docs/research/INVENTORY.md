# GĐ2 research inventory

Audit base: `b9cc4352055ddfd9d62c6450e88ef4aaf5d658ba`, 2026-11-01. Code evidence, not a rerun of the historical experiment. Requirements: finishing plan section 4, with section 5 identifying implementation gaps.

| Area | Present | Missing / mismatch before GĐ2 |
|---|---|---|
| Scenarios | `research/scenarios.py`: 35 = 7 vectors × 5 goals, version v1.1 | 36th direct scenario; substantially reused payload templates |
| Models | `research/run.py` accepts CLI model list; digest available via Ollama tags | Defaults and product Lab launcher list Qwen7B + Llama3.2 3B, not required Llama3.1 8B; no API provider adapter |
| Profiles | naive / baseline / defended; D1–D10 labels and omit switches | Lab definitions approximate product; intent D3 uses golden expected tool; D10 says masked trace but legacy row has raw answer/arguments |
| Ablation | `run.py --ablations`: one case/vector, one repeat, all selected models, defended minus Di | Required 36 ×10 ×5 on primary local; RQ2 standalone add-one design is different |
| Sandbox | `research/sandbox.py` restricts resolved directory to `.local/research/<run>/`; SQLite backup reset, real balanced synthetic journals, reconciliation | Simulates proposals and many tools return generic success rather than full banking data; not end-to-end backend/OTP execution |
| Ingestion | `Sandbox.source()` writes/reads `lab_sources`; engine inserts fixture tool response/history directly | None of six indirect vectors is injected via real banking/KB/provider/conversation API in this runner |
| Agent service | `agent_service/main.py`: separate HTTP-only process, delegated tools, multi-round loop, output filtering via backend, total tokens and terminal reasons | Research engine calls Ollama directly and bypasses agent service; cannot infer product security from lab ASR |
| Seed | Engine passes `20261101 + repetition` in Ollama options | No seed column in result; temperature .2 instead of 0; classifier has no seed; product service temperature 0 but no explicit seed |
| Trace | Rows include tool names, arguments, allow/deny, events; product has `agent_runs`, `agent_calls` | No research trace ID or foreign key to `agent_runs`; no API ingestion evidence |
| Utility | 100 generated questions (60 base paraphrases +40 extras), 14 tool categories | Required 80 grounded tasks and ~20% multi-step; scorer only checks an ALLOW for expected tool and subset of args; no final value correctness; empty expected args too weak |
| ASR | `engine.evaluate()` deterministic canary/tool flags, no LLM judge | Accepted wrong proposal counts as success even pending human approval; card proposal can count as lock; phishing numeric/URL substring may count quoted refusals; separate committed harm needed |
| False positives | Correct expected tool/args denied; ten benign classifier snippets separately | Does not cover all legitimate defense stops/pre-model blocks/output filters; not end-to-end FPR |
| Cost | Per-row wall time/input/output tokens; classifier records separate cost | Main row excludes cached classifier time/tokens; no median; one model decision only; zero tokens also used on request error |
| Provenance | Dataset/engine SHA256, model name, repetition, scenario version | No digest/snapshot/prompt hash/code commit/seed column/run linkage or full hardware metadata |
| Resume | JSONL flush per row, interrupted summary | New run directory each launch; cannot skip already-completed immutable cells on resume |
| Statistics | `run.aggregate()` and `scripts/research-report.py` produce point rates, mean timing, CSV/SVG | No Wilson CI, paired cluster bootstrap, error bounds, separate harm metrics; legacy report contains hard-coded narrative/counts |
| Git hygiene | `.env`, `.env.*`, `.local`, DB/sidecars and `*.log` ignored | Ignore rules do not block force-add or secret text in arbitrary files; old tracked `docs/release/research/raw-results.zip` is synthetic raw experiment output. Do not reuse publisher for new raw logs. |

The GĐ2 pilot adds explicitly labelled seed/temperature metadata and observation IDs, timing/accounting output and a dry/offline-tested API adapter. It does **not** close the real-ingestion, complete utility, agent-trace, resume or formal statistics gaps. Those belong to GĐ3. No product route/service edits are authorized in this phase.

## GĐ3 work queue

1. Review/freeze protocol decisions (especially add-one vs legacy leave-one-out), choose `<API_MODEL>`, immutable snapshot and budget.
2. Add direct scenario #36; freeze 80 utility tasks and 16 multi-step tasks with DB-derived expected values and exact argument predicates.
3. Build research-only real API poisoning and retrieval fixtures; record actor access, source IDs and exposure. Keep all effects on isolated DBs.
4. Drive real delegated multi-round agent, link observation IDs to `agent_runs`/`agent_calls`, pin seed/digest/prompt/snapshot; resolve product-bound integration changes with user before changing production code.
5. Implement strict final-answer utility, denial/stop FPR, proposal vs committed-harm scoring and refusal-safe phishing predicates; red→green tests.
6. Durable per-cell resume, immutable attempt history, complete error/usage accounting and model/seed support checks.
7. Wilson intervals, paired scenario bootstrap, CSV/tables/plots from data and coverage checks for the exact matrix; replay comparison.
8. After approval, run 10 API cost pilots; estimate money from actual tokens/current provider rates and obtain budget approval. Then 7 vectors ×3 models ×3 profiles plus 10 utility smoke questions before GĐ4.

AI-14, PI-05 and PI-06 remain unverified by this phase. Historical synthetic results must not be relabeled as the new protocol's evidence.
