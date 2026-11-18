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
- [x] Phase 1: fixtures/documents + reproducible generator; validate existing seed with tests and consistency script, add pentest-row cleanup only on disposable data. Tests first, then phase commit.
- [x] Phase 2: backend/app/documents/{repository,extract,service}.py and routes_documents.py; migration 21. API tests DOC-API-01..12 fail first then pass. Authenticate before bounded multipart parsing; scan each chunk and filename, fail closed; use existing Ollama embed endpoint. Commit.
- [x] Phase 3: documents/reader.py and gateway integration. AskDocumentArgs(document_id,question), owner repository, top4, strict schema, P/intent/provenance/spotlight/policy/disclosure/events. Regression tests all configs, unknown rule, P capture, alias, follow-up risk and mixed actions. Commit.
- [x] Phase 4: My documents screen using existing styles, /documents navigation and chat selection; browser tests upload/list/status/delete/ask and mobile. Commit.
- [x] Phase 5: one-command runner creates JUnit + HTML + ID-complete report; deterministic API/security tests and optional measured real-model evaluation, baseline comparison. All prior backend/research/frontend checks. No fabricated live results. Commit.
- [ ] Phase 6: DOCUMENT_RAG.md seven sections, FUNC_API_TEST_REPORT.md, demo script and completion; independent review, fixes, PR (no merge).

Sources consulted: https://fastapi.tiangolo.com/tutorial/request-files/ ; https://pypdf.readthedocs.io/en/stable/user/extract-text.html ; https://docs.ollama.com/api/embed . pypdf cannot OCR scans; extraction can expand streams, so enforce extraction budgets. Ollama truncate=false avoids silently incomplete embedding input.

## Evidence 2026-11-18
- Phase 1 fixtures: committed 0354c1a; fixture plus fixed-seed checks 4 passed. Existing seed already has 62 users / 125 accounts / 4150 transactions; consistency/cleanup helper remains.
- Phase 2 API: 14 passed, then integrated document API/gateway/boundary/FIELD_TRUST suite 40 passed. Oversized-body middleware and pypdf 7 configuration regressions reproduced and fixed.
- Ruling: explicit LLM_PROVIDER=mock uses labeled deterministic embeddings; real providers never fall back. This keeps offline demos executable without misrepresenting model measurements.
- Ruling: expand FIELD_TRUST coverage fixture to exercise new ask_document tool with owned document and exact read intent; do not loosen capability permissions to satisfy registry test.
- Phase 4 initial browser check passed desktop/mobile upload/list/question/delete; visual pass found plain form fields, switched to existing Field/card components. No CSS/theme changes.
- Real-runtime preflight: cached nomic-embed-text returns 768-dimensional vectors. Main venv lacks torch; found already-provisioned D:/NovaBank-Week8-Lab/runtime with torch and transformers. No runtime dependencies installed.

## Independent review and consolidated fix pass
Reviewer: /root/document_rag_review, fresh context gpt-6.2-astra. Nine important findings; no implementation edits by reviewer.
- Selected-document intent binding, bare alias grammar/restoration scope, cross-tool audit prose, staff read-only capabilities and document-wide P: 12 failing repro cases before fixes.
- PDF array-stream assembly cap, deletion during baseline preview, failed retrieval audit target/rule: 3 failing repro cases before fixes.
- Fixed the above in one implementation pass; focused API/gateway/boundary/review suite 66 passed. Extra reader deletion race, concurrent reservations, invalid embeddings, legitimate subsequent bank balance, and strict live-oracle tests: 28 passed.
- Replaced per-chunk P vaults with document-wide entity discovery before every model boundary; no shared/global Pseudonymizer change.
- Audit minimization follows document-exposed conversations; preserve typed bank facts and safe IDs for existing bank-owned output rendering, hash free-form prose.
- Final restoration accepts only aliases actually supplied in document result plus identities present in the user's current request. C/D isolated answer aliases are additionally limited to cited source text.
- Full pre-review-fix rerun: 985 passed, 2 skipped, 1 xfailed (known test fixture short signing key warning). Final whole-suite rerun required after this fix pass.
- Ruling: freeze real-model application source before measurement. Earlier live A/B pilot used old code; when later lazy imports saw edited code, C failed due mixed source versions. Campaign stopped and preserved as superseded, never release evidence. Reviewed campaign must run from a detached immutable worktree.
- Baseline replay completed on detached 099577f at sibling .local/document-rag-baseline; copied original local A-J harness changes only ROOT/URL/DB/log destinations. Original demo and harness untouched.

- Reviewed whole suite: 1,014 passed, 2 skipped, 1 xfailed; all 50 Playwright cases passed. Python/JavaScript lint, component checks and build passed.
- Additional real-runner fixes: independent DB per baseline configuration (positive TOTP enrollment otherwise breaks later login), execution-manifest validation, declarative alias/link fixtures with unchanged screening. Five focused fixture/oracle tests passed; rendered both new PDFs.
- Coverage exposed a low-probability UUID/hash masking collision in audit metadata. Fixed-ID reproduction failed before the correction; strict typed UUID4/SHA-256 preservation passed 79 document/security-event tests. Final coverage/research rerun completed; see final acceptance evidence below.
- Actual seed validation: 62 users, 125 accounts, 4,090 transactions; 2 zero-balance accounts, 1 pending draft, balanced ledger and no pentest fixture row.

## Real-model findings resolved before final acceptance
- Corrected filename attribution to retain ordinary underscores; two A/D reproductions failed before the fix.
- Clarified isolated-reader money fields (interest percentages are not monetary amounts) with a schema pattern and an explicit fact-extraction prompt. Real loan/invoice/payment-notice probes validated the result; no schema fallback was introduced.
- Pure document questions now receive document-specific citation guidance. Real C responses had invented KB-benign citations and were correctly rejected by the existing knowledge gate. The gate remains unchanged; a service integration test proves invented KB citations are still refused. Forty-three prompt/spotlighting/document tests passed.
- Fixed stdlib trace basename collision between SymPy products.py and app/products.py. Full-path instrumentation records only the five configured financial modules; every backend test still executes.
- A/B attack outcomes remain observations; C/D security, all-config ownership/P, and all-config benign utility are acceptance gates. Missing trials or infrastructure errors never pass.
- Disk-full interrupted one campaign. Obsolete pytest databases were archived, not discarded, under D:/NovaBank-Week8-Lab/document-rag-evidence/pytest-archive. Interrupted campaigns are superseded. Application source is frozen at da593f8 for the final measurement.

- Final frozen-application Python regression: 954 backend + 70 research = 1,024 passed; 2 opt-in licensed-model skips, 1 existing xfail. Financial executed-line coverage 94.17%, pytest exit 0. Evidence: .local/doc-verified.xml, .local/doc-final-oracles.xml, .local/doc-verified-coverage.log.

- Final observer corrections preserve raw evidence: C6 known-input ID echo is adjudicated only from complete DB transcripts; deliberate ANOMALOUS_SEQUENCE is distinct from runtime outage and still requires all security assertions. Research suite: 70 passed. Full D configuration rerun; application/policy hashes unchanged.

- Final real-model acceptance: PASS, 120 trials (A/B/C from da593f8; all 30 D trials rerun with 6a5772f observer, identical application/policy hashes). C/D required cases and all-config ownership/P/benign utility passed. A URL reflection remains a 3/3 positive control. Consolidated JUnit/HTML: .local/document-rag-evidence/reviewed/report.html.
