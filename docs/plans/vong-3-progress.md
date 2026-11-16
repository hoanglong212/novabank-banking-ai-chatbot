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

## Step 0b — concrete transfer scaffold

- New R2 scaffold renders actual seed account IDs: authorized Bob versus attacker
  Charlie. No `W8_` marker appears anywhere in rendered payloads/user turns.
- Initial legitimate transfer request contains only Bob, never Charlie; the
  attacker recipient appears only in the untrusted source. This preserves the
  provenance contrast instead of granting authority in an introductory legend.
- Three RED→GREEN research tests verify all 40 rendered cases, real target
  substitution, language/channel counts, QR 80-character bounds, capability
  prompts and fixed sampling schedule. No model inference used in these tests.
- Corpus adaptations cite pinned AgentDojo sources and the Crescendo paper;
  fixed staged examples are not claimed to implement an adaptive search attack.
- Actual seed ownership, balances, native calls and proposals remain runtime
  checks to be registered and measured; file presence is not a utility result.

## FIELD_TRUST coverage test (chỉ thêm test)

- `backend/tests/test_field_trust_coverage.py` gắn marker riêng vào 16 cột chữ tự do do
  bên thứ ba ghi được, gọi **mọi tool đọc** trong registry (khách và nhân viên, tất cả ALLOW),
  rồi duyệt kết quả ngân hàng thô (trước bộ lọc quarantine). Cả 16 cột đều tới ít nhất một tool.
- Test **fail** → đánh dấu `xfail(strict=True)`, **không sửa `provenance.FIELD_TRUST`**.
  Khi FIELD_TRUST được sửa, test sẽ XPASS và báo đỏ để gỡ xfail.
- Trường thiếu trong FIELD_TRUST (tool.key ← bảng.cột):
  - `get_bills.customer_code` ← `bills.customer_code`
  - `list_audit_events.reason_code` ← `banking_audit.reason_code` (FIELD_TRUST chỉ có `detail`/`details`)
  - `read_ticket.text` ← `knowledge_documents.content` (trích chính sách nhúng trong ticket)
  - `read_ticket.title` ← `knowledge_documents.title`
  - `search_knowledge.source` ← `knowledge_documents.source`
- Ghi chú phạm vi: các cột trong tài liệu kiến thức chỉ hiện khi tài liệu ở trạng thái
  `PUBLISHED`/`approved` (nhân viên duyệt); vẫn tính là chữ không do logic ngân hàng tạo ra.
  Test không đánh giá cột ngoài 16 cột đã liệt kê (ví dụ hồ sơ người dùng).
