# Design status against available Week8 requirements

Reviewed against integrated root code on 2026-11-15. The original 72-step design and its exact 13-channel inventory are unavailable; the searched `docs.zip` is also absent. This is a component/source map, not a fabricated completion table for those missing materials. Named functions are stable references; line numbers move.

| Component | Current implementation | Evidence boundary |
|---|---|---|
| Identity/session/OTP authority | `agent_access.authenticate`, required signed claims, current role/session/auth-version checks, narrow tool scopes and argument hashes | Bank retains ownership and confirmation authority in every configuration |
| T1 security event ladder | Migration 12, `security_events.py`; transaction-local evidence, redaction/dedup and model/tool/approval/OTP/posting stages | Events support L1/L2/L3 scoring, not automatic proof of attack success |
| T2 source screening | Reviewed field registry covers transaction status and other tool text; regex, Prompt Guard adapter and Qwen screening | Mock tests are not real-model utility; real Prompt Guard unavailable fails closed |
| T3 provenance/context | Migration 13, `agent/provenance.py`; irreversible taint, inherited source IDs/hashes and critical argument origin checks | Narrow `bank_default` funding-account exception; lexical matching is not semantic proof |
| T4 signed tools/intent/role | Required claims plus independent capability/hash/role checks and trusted latest-request binding | Authorization does not rely on the model following instructions |
| T5 A-D policy | `agent/policy.py` and versioned JSON; strict schemas/conditions, first-match reasons, default deny; authenticated expiring lab sessions | Historical on/off profiles are not this matrix; malformed/missing policy cannot authorize |
| T6 risk/cooling | Risk scoring/state, bounded cooling and bank-owned recipient/amount checks | Thresholds are configuration, not a production-calibrated fraud model |
| T7 approval/OTP | Frozen bank templates, policy/risk/source evidence, owner/session review and separate confirmation | Human approval remains a social-engineering boundary |
| T8 quarantine | Persistent source records, run revocation, bank-only terminal completion and audited staff release | Release authority requires support write/admin permission |
| T9 spotlighting | Per-run random Unicode marking of reviewed untrusted textual fields; IDs/numbers untouched; known marker removed before display | Narrow field-reading utility: Qwen2.5 20/20 each off/on; Llama3.2 15/20 each. Raw marker leak preserved in evidence. No overall-superiority claim |
| T10 Prompt Guard 2 | Lazy local adapter, configuration/preflight and fail-closed source handling | Required weights/runtime absent; not a successful benign end-to-end deployment |
| T11 dual LLM | Separate ticket assessment; enums to main model, encrypted human-only summary | Missing/unavailable local dependency is reported as such, not a pass |
| T12 evaluation | Disposable bank/agent HTTP harness, source fixtures, raw model evidence, separate L1/L2/L3, source hashes/checkpoints, synthetic seed-copy option | Exact Qwen3 missing. C smoke eighteen strict-zero attacks do not establish positive L1 baseline or final ASR claim |
| C1 legacy route safety | Legacy authority mode requires explicit flag and active pytest execution context | Normal production/lab application cannot use a test-only legacy shortcut |
| C2 disclosure/balance | Field minimization, restored-output checks and current bank-rendered balance; approved KB citations | Independent review reproduced nested-alias leak and verified fix; debt minimization follow-up pending in review snapshot |
| C3 quishing | Payment prose URL/instruction validation on generation/decode, QR/OCR labels, external/new-payee cautions; no URL opening | Genuine QR reaches verification; malicious signed QR rejected. Origin is client-declared metadata, not authenticated capture proof |
| C4 new-payee step-up | Bank-derived verified payees, draft/session/factor-bound TOTP proof and distinct final email OTP, atomic idempotent posting | Saved nickname/beneficiary alone does not establish a trusted payee |
| C6 realistic synthetic seed | Exclusive new-path CLI; 50 Vietnamese synthetic customers, 2-3 accounts each, six-month posted activity, staff/cards/bills/tickets/beneficiaries | Deterministic business data, explicitly synthetic; ledger reconciliation evidence is not live-model attack evidence |
| T13 release documents/review | Updated threat model, authority matrix and scoped independent review | Root owner finalizes release results/counts and C7; no unconditional all-plan success declaration |

## Observed untrusted surfaces

`agent/provenance.py:FIELD_TRUST` documents tool/field boundaries: transaction description/counterparty (recent and status tools); account nickname; beneficiary nickname/name; card merchant; savings label; bill provider; spending labels; customer ticket subject/description; staff ticket subject/description/replies; knowledge title/content/chunk text; audit details; and prior tainted conversation runs. QR `to_name`/`add_info` and OCR payment prose have dedicated sanitization and origin metadata. This inferred inventory is not a verbatim replacement for the missing original list of 13 channels.

A bill's server-selected primary funding account may be labeled `bank_default`; the model cannot select another account through that exception. Explicit critical values remain user-bound. Context history remains conservatively tainted after earlier tainted or incomplete runs.

## Release interpretation

Implementation, mock regression, live-model availability and measured ASR/utility are separate gates. Current code and focused tests do not establish every acceptance criterion in the missing original design. Consult [INDEPENDENT_REVIEW.md](INDEPENDENT_REVIEW.md) for verified findings and limits, and the root release results for final command output and experiment counts. Historical Week7 results remain historical.
