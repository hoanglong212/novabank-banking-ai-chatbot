# R2 execution ledger

Authoritative user instructions: [verbatim prompt](vong-3-agent.md), committed first as `3697800`.
No model inference for R2 has run. Existing stack, dependencies, qwen2.5:7b,
local original Prompt Guard weights, and isolated runtimes are retained.

## Step 0a — positive parameter provenance

- Found `validate` denied only exact UNTRUSTED hashes, otherwise returned missing
  origins for downstream policy. Generic canonical arguments were also accepted.
- Seven RED cases cover normalized memo-only accounts, changed amount, contact
  fields, normalization positive controls, and partial/unverified canonical values.
- Require normalized complete values in user text or the bank-selected primary
  own funding account. Amount spelling uses the existing bank numeric parser
  for explicit `10.000 VND` / `10k`; it excludes memo text and never trusts a
  provided canonical amount by itself. IDs cannot match prefixes of longer IDs.
- New reason `PARAM_NOT_FROM_USER`, rule `T4-bind`; hash matches remain secondary
  evidence. Risk/quarantine recognize the new reason.
- Additional RED caught loss of audit detail when the proposal transaction rolls
  back. The denial carries bank-owned detail to the committed gateway event.
- GREEN: 69 targeted provenance/gateway/account tests, 19.18 s; Ruff/whitespace clean.
- Existing tests expecting the old reason were updated to the explicitly requested
  reason; their DENY/halt/no-proposal assertions remain intact.

## Decisions before measurement

- No `engineering.json` is configured; use actual pytest and Ruff commands.
- Preserve R1 rubric for L1/L2/L3, add separately registered L1-answer evidence.
- QR remains a lab bridge; report actual parser verdict separately. No production
  ingestion or account-creation tool is added. M-ACCOUNT is excluded.
- All application, harness, corpus and scorer work must finish before the snapshot
  and immutable preregistration. No labels/protocol changes after inference.
