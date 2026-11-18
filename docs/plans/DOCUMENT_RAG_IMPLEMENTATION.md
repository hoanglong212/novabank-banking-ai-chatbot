# Document RAG implementation plan

> Execute inline with msi-aef-executing-plans. User authorized autonomous design decisions and research on 2026-11-18; retain the existing design system and stop at a PR.

Goal: owner-isolated document Q&A through the existing bank gateway, with reproducible API/security evidence.
Architecture: Bank-owned upload/repository/ingestion/retrieval; existing P, screening, quarantine, provenance and capability boundaries; isolated schema-only reader for C/D. No new write tools or vector service.
Stack: existing FastAPI/SQLite/React/Ollama; pypdf, numpy and python-multipart (the standard FastAPI parser, justified by official docs).
Spec: docs/plans/DOCUMENT_RAG_SPEC.md. Discovery: docs/release/week8/DOCRAG_DISCOVERY.md.

## Rulings resolving discovery
- Preserve actual role/token ordering. Add explicit allow-rule enforcement for ask_document only; wildcard approval rules cannot authorize this read.
- Neutralize source-authored pseudonym tokens before P; only server-created aliases can be restored. P applies before embedding, screening and isolated/main inference. Store extracted text only, no original file.
- Document text is not audit material: persist metadata/hashes in agent/security traces. Output document references use authenticated repository lookups; no raw source in logs.
- New upload uses python-multipart; pypdf and numpy are explicit bounded dependencies. No automatic model download. Missing runtime is ERROR, never PASS.
- Conversation labels remain conversation-scoped and monotonic. Preserve A/B ablations and all existing tool semantics.
- Missing AGENT_TEST_PLAN_FUNC_API.md: use all supplied DOC IDs verbatim plus the existing route-matrix format; record the absent external template, never claim it was read.
- Retry scan_failed by re-uploading identical bytes; reuse that user's failed document slot. Reject unsafe formats; TXT/MD have no distinct magic, require strict UTF-8 without binary signatures/control bytes.
- UI reuses existing navigation/service cards/buttons/sheets and CSS tokens; do not edit the theme or global CSS.

## Global constraints
5 MiB, 50 pages, 200 chunks, 20 active documents/user; chunks 800 chars with 100 overlap; top-k 4. Owner is always server session. Generic 404 for foreign/deleted/unready tool target. No OCR; read-only ask_document. Schema answer <=500 chars. No main merge.

## Review focus
Concurrent upload quota/deletion during inference; binary spoof/PDF decompression; foreign IDs and canaries in errors/logs; fake alias collisions and mixed transfer/document requests; detector/model outage and nonfinite/mismatched embeddings. Pin these with repository, API, gateway and schema tests.

## Tasks / ledger
- [x] Phase 0: discovery committed dfcbbea; no feature code.
- [ ] Phase 1: fixtures/documents + reproducible generator; validate existing seed with tests and consistency script, add pentest-row cleanup only on disposable data. Tests first, then phase commit.
- [ ] Phase 2: backend/app/documents/{repository,extract,service}.py and routes_documents.py; migration 21. API tests DOC-API-01..12 fail first then pass. Authenticate before bounded multipart parsing; scan each chunk and filename, fail closed; use existing Ollama embed endpoint. Commit.
- [ ] Phase 3: documents/reader.py and gateway integration. AskDocumentArgs(document_id,question), owner repository, top4, strict schema, P/intent/provenance/spotlight/policy/disclosure/events. Regression tests all configs, unknown rule, P capture, alias, follow-up risk and mixed actions. Commit.
- [ ] Phase 4: My documents screen using existing styles, /documents navigation and chat selection; browser tests upload/list/status/delete/ask and mobile. Commit.
- [ ] Phase 5: one-command runner creates JUnit + HTML + ID-complete report; deterministic API/security tests and optional measured real-model evaluation, baseline comparison. All prior backend/research/frontend checks. No fabricated live results. Commit.
- [ ] Phase 6: DOCUMENT_RAG.md seven sections, FUNC_API_TEST_REPORT.md, demo script and completion; independent review, fixes, PR (no merge).

Sources consulted: https://fastapi.tiangolo.com/tutorial/request-files/ ; https://pypdf.readthedocs.io/en/stable/user/extract-text.html ; https://docs.ollama.com/api/embed . pypdf cannot OCR scans; extraction can expand streams, so enforce extraction budgets. Ollama truncate=false avoids silently incomplete embedding input.

## Evidence 2026-11-18
- Phase 1 fixtures: committed 0354c1a; fixture plus fixed-seed checks 4 passed. Existing seed already has 62 users / 125 accounts / 4150 transactions; consistency/cleanup helper remains.
- Phase 2 API: 14 passed, then integrated document API/gateway/boundary/FIELD_TRUST suite 40 passed. Oversized-body middleware and pypdf 7 configuration regressions reproduced and fixed.
- Ruling: explicit LLM_PROVIDER=mock uses labeled deterministic embeddings; real providers never fall back. This keeps offline demos executable without misrepresenting model measurements.
- Ruling: expand FIELD_TRUST coverage fixture to exercise new ask_document tool with owned document and exact read intent; do not loosen capability permissions to satisfy registry test.
- Phase 4 initial browser check passed desktop/mobile upload/list/question/delete; visual pass found plain form fields, switched to existing Field/card components. No CSS/theme changes.
- Real-runtime preflight: cached nomic-embed-text returns 768-dimensional vectors. Main venv lacks torch; found already-provisioned D:/NovaBank-Week8-Lab/runtime with torch and transformers. No runtime dependencies installed.
