# NovaBank reliability fixes

**Goal:** Resolve T01, T06, T07, T08, T15 and unstable T05 from the recorded live evaluation.

**Spec:** `docs/NOVABANK_TEST_REPORT_2026-10-16.md`, authorized by user: “bắt đầu theo kế hoạch”.

**Architecture:** Keep native Ollama tool proposals and the existing authorization dispatcher. Bind known banking requests to user-provided IDs/default principal; render authoritative results in application code. Never interpret raw JSON content as an executable tool request. A reachable model with malformed/missing tool calls may use an explicitly reported, deterministic fallback for a clearly recognized request. Unavailable Ollama remains a 503. Greeting uses a fixed safe capability description. Unknown intent gets approved FAQ retrieval, not arbitrary side effects.

**Stack:** Existing FastAPI/Pydantic/httpx/pytest and React/TypeScript/Vite; no installs.

## Tasks

- [x] Add failing regression tests for malformed replies, hallucinated IDs, grounded balance/transaction/ticket replies, denied ownership, unauthorized ticket proposals, negative ticket requests, repeated ticket proposals and unavailable Ollama.
- [x] Implement request binding and grounded replies; expose response_source so model-selected calls and application fallback are distinguishable.
- [x] Reproduce T15 with actual browser switching; replace shared request invalidation with independently cancelled effects and user-scoped active selection. Reset stale drafts/results on identity change.
- [x] Run complete pytest suite and frontend build. Run the unchanged 15 prompts and repeat critical cases against live Ollama; keep baseline evidence intact.
- [x] Review changes and record actual results, remaining risks, and model-versus-application attribution.

## Review focus

Foreign/unknown IDs must never be replaced by the current user's account. A model cannot create a ticket without user intent. Malformed text is not executable. Tool calls with invalid shape must not crash. Follow-ups must use user-originated context. Both Alice and Bob must retain their own history during fast switches. No result from a stale request may repopulate the other identity's view.

## Ledger

Implementation is inline using msi-aef systematic debugging, TDD, verification and review. No independent reviewer is authorized; self-review will be identified as such.

Implementation and configured checks completed. Evidence: `docs/reliability-completion.md`. Self-review completed; independent review remains pending (no reviewer dispatched under local framework adaptation).
