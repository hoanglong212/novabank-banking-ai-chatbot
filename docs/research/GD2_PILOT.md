# GĐ2 local pilot - measured results

2026-11-01 (Asia/Saigon). **Operational pilot only; not an official experiment or AI-14/PI-05/PI-06 result.**

Protocol commit: `00be39ad26627f25e20b77794101796ad159e030`. Pilot/adapter code commit: `397783c3fde56d09e5b167e80e2dcb2835a8e2c8`; clean working tree at execution. No push.

## Execution

- Command: `backend/.venv/Scripts/python.exe -m research.pilot`.
- 72/72 observations: 7 attacks × 3 profiles × 2 models + 5 distinct utility tasks × 3 profiles × 2 models; 0 transport/parsing errors; 0 output-length stops.
- 62 main-model invocations; 10 cases blocked by D7 before generation. Six cached Qwen classifier calls are separate.
- 72 sandbox ledger checks balanced. Final reconcile: total 0, no mismatches/unbalanced journals. Demo DB accessed only by read-only snapshots; financial hashes/balances/counts unchanged.
- Intel i7-10700K, ~32 GiB RAM, NVIDIA RTX 3070; Ollama reports 100% GPU for the loaded model. Local download of Llama3.1:8b was explicitly approved; no library installation.
- Total measured pilot elapsed time: **175.453 s** (2.92 minutes), excluding model download and regression tests.
- Generation: temperature 0, seed 20261101, one decision, context 4096, output cap 160; indirect data is a SQL lab fixture. The official multi-round path is not measured.

## Timing and token counts

Wall time includes sandbox reset and model loading, but excludes the separately cached classifier. Averages include the five pre-generation blocked cases per model (zero main-model tokens). Tokens are Ollama counters, not estimated characters.

| Model | N | Mean wall s | Median wall s | Mean input tokens | Mean output tokens | Mean total main tokens | Mean logical s including D7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5:7b | 36 | 1.484 | 1.260 | 641.61 | 37.61 | 679.22 | 2.639 |
| llama3.1:8b | 36 | 2.213 | 1.151 | 480.61 | 26.31 | 506.92 | 3.368 |

Six classifier calls physically consumed **41.748 s / 841 tokens**. The first call included 40.414 s loading Qwen; classifier mean excluding reported load time was 0.220 s. Main-run reported load time summed to 4.841 s (Qwen context change) and 37.262 s (Llama). Do not multiply cold-start costs as if every call loads weights.

Logical cost charges each D7-consuming observation its cached classifier latency/tokens; it is **not** the physical elapsed time. Mean logical tokens were 698.86 (Qwen) and 526.56 (Llama). D10 removed the foreign-memory source before D7, so that case does not consume classifier work.

| Model | Profile | Kind | N | Mean wall s | Median wall s | Mean input | Mean output | Mean logical s |
|---|---|---|---:|---:|---:|---:|---:|---:|
| llama3.1:8b | baseline | attack | 7 | 1.484 | 1.216 | 463.00 | 35.29 | 1.484 |
| llama3.1:8b | baseline | legitimate | 5 | 1.192 | 1.168 | 790.00 | 24.20 | 1.192 |
| llama3.1:8b | defended | attack | 7 | 0.436 | 0.070 | 107.00 | 6.86 | 6.377 |
| llama3.1:8b | defended | legitimate | 5 | 1.278 | 1.302 | 357.20 | 24.20 | 1.278 |
| llama3.1:8b | naive | attack | 7 | 7.064 | 1.395 | 478.71 | 41.29 | 7.064 |
| llama3.1:8b | naive | legitimate | 5 | 0.887 | 0.875 | 845.00 | 24.20 | 0.887 |
| qwen2.5:7b | baseline | attack | 7 | 1.965 | 1.773 | 891.14 | 55.29 | 1.965 |
| qwen2.5:7b | baseline | legitimate | 5 | 1.209 | 1.033 | 756.40 | 36.20 | 1.209 |
| qwen2.5:7b | defended | attack | 7 | 0.330 | 0.024 | 103.29 | 8.29 | 6.271 |
| qwen2.5:7b | defended | legitimate | 5 | 1.331 | 0.978 | 342.20 | 38.80 | 1.331 |
| qwen2.5:7b | naive | attack | 7 | 2.559 | 1.920 | 943.14 | 48.71 | 2.559 |
| qwen2.5:7b | naive | legitimate | 5 | 1.350 | 1.052 | 808.40 | 38.60 | 1.350 |

## Machine-time projection (provisional)

Section 4 contains **4,320 local + 1,260 API runs**. PI-06 adds 540 primary-local attack runs. API latency, provider tokens and money were not measured; a total that includes the remote API cannot yet be given honestly.

Formula per local model: `540 × mean_attack_seconds + 720 × mean_utility_seconds`. Ablation proxy: `1,800 × primary_naive_attack_mean + 150 × classifier_mean` (30 indirect scenarios × 5 repeats in the D7-only arm). Replay: `540 × primary_attack_mean`. Divide by 3,600 for hours. Inputs are the observed profile-balanced means; one vector example and five utility categories are weak cost samples.

| Basis | Section 4 local | Including PI-06 |
|---|---:|---:|
| Warm-capacity calculation, removing Ollama-reported load durations | 1.84 h | 2.06 h |
| Direct extrapolation of observed means, including observed load effects | 3.34 h | 3.88 h |
| Sensitivity: 2× observed-mean proxy | 6.68 h | 7.76 h |
| Sensitivity: 4× observed-mean proxy | 13.35 h | 15.51 h |

These are capacity scenarios, **not a confidence interval, guaranteed range or official runtime forecast**. The observed-mean calculation deliberately shows cold-start sensitivity; the warm calculation excludes loading rather than pretending it repeats on every turn. Official execution uses larger context/output limits, real API retrieval and up to four rounds, plus layer overhead not measured here. Alternating Llama with a Qwen D7 classifier can force model swapping on this GPU; the cached pilot does not measure that cost. GĐ3 must remeasure the real multi-round path and decide/document classifier caching, adding actual loads and any local classifier work for the API model. Do not reduce the matrix based on this pilot.

## API and repository checks

- API adapter configuration check: key absent, transport disabled, network calls 0. MockTransport tests cover offline wire format, usage, tool normalization, key masking, error redaction and disabled-by-default behavior. No API provider selected; `<API_MODEL>` remains unchanged.
- `.env`, `.env.local`, research `.env`, `.local/research/`, SQLite files, MFA key files and logs are ignored. No forbidden paths in tracked/candidate files or matching Git path history; no credential-pattern/known-config-secret findings in scanned files, including the historical synthetic result archive. This is evidence of the checks performed, not a guarantee against future force-add or unknown secret formats.
- `docs/release/research/raw-results.zip` predates GĐ2 and contains synthetic historical observations. No new raw result/log/DB/key was staged or published.

## Validation and review

- RED: `python -m pytest research/tests -q` -> 13 failures for missing behavior; GREEN -> 13 passed.
- `PYTHONPATH=backend python -m pytest backend/tests research/tests -q` -> **372 passed** (128.10 s).
- `npm run test:components` -> **17 PASS groups**.
- `npm run test:e2e` -> TypeScript/Vite build + **16 passed** (1.7 min); disposable DB on port 8092.
- After adding classifier load telemetry, 13 research tests passed again and the full 72-case real-model pilot passed. No product code changed.
- Reconcile only the disposable research DB; read-only demo comparison; Git diff/secret checks. No hosted CI run because there was no push.
- Self-review by the implementing agent. Independent review/user protocol approval still pending. Existing CI currently collects backend tests only; add the explicit research/tests command in GĐ3 when workflow changes are authorized.

## Local evidence and provenance

- Run directory (gitignored): `.local/research/pilot-gd2-20261101-230307-632896/`.
- Raw JSONL SHA-256: `55bc37a0373207f253b7610367f775a882fe9df184a6b32f1c0f89e42ad243e3`.
- Protocol bytes SHA-256 at run: `fba22912c1416c082f0b17f9ada49ea4c2a2a736dd3f1ab3b5346115fac76b7f`.
- qwen2.5:7b digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
- llama3.1:8b digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
- Local-only analysis and verification: `.local/gd2/pilot-analysis.json`, `analyze_pilot.py`, `git-hygiene.json`, demo-before/after snapshots and test logs.

Next work is listed in [INVENTORY.md](INVENTORY.md#gđ3-work-queue). No official ASR, utility acceptance, defense ranking or replay claim is made.
