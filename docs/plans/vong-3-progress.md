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

## Sửa FIELD_TRUST trước khi đo (quyết định của người dùng)

- Thêm cả 5 trường vào `provenance.FIELD_TRUST`: `get_bills.customer_code`,
  `list_audit_events.reason_code`, `read_ticket.text`, `read_ticket.title`,
  `search_knowledge.source`. Bỏ `xfail`; `test_field_trust_coverage.py` pass thật.
- Lý do: một cột chỉ có một nhãn bất kể tool nào đọc; `search_knowledge` đã coi nội dung
  `knowledge_documents` là UNTRUSTED, nên `read_ticket` và trường `source` phải nhất quán;
  mặc định từ chối.
- Hệ quả đã biết: `customer_code` và `reason_code` luôn có giá trị, nên mọi lượt đọc
  `get_bills` / `list_audit_events` giờ gắn nhãn run UNTRUSTED.
- Snapshot cũ `6729f60` bị thay thế; snapshot mới ghi trong [prereg](vong-3-prereg.md).

## Đợt sửa 1 — Bước 1: cấu hình A giữ kiểm tra vai trò

- Sửa `backend/app/agent/agent_access.py`. Kiểm tra `ROLE_NOT_PERMITTED` trong `execute_tool`
  giờ luôn bật, không còn điều kiện `not off`. Ở A, token của khách hàng chứa
  `set(MODELS) - set(staff_tools.PERMISSIONS)`; token của staff ở A giữ nguyên `set(MODELS)`
  (khi tắt intent_binding, A không dùng token để giới hạn tool). Mọi lớp khác của A vẫn tắt,
  kể cả `staff_tools.execute(..., bound=not off)`.
- Hệ quả có chủ đích cho staff: ở A, staff gọi tool của khách hàng giờ cũng bị `ROLE_NOT_PERMITTED`
  (cùng một điều kiện vai trò như ở B/C/D).
- Test mới: `backend/tests/test_config_a_role_boundary.py`. Trên code cũ: RED ở
  `test_customer_at_a_gets_no_staff_tools_and_is_role_checked` (token có tool staff).
  Các test staff ở A và B/C/D pass cả trước lẫn sau; đó là test giữ hành vi.
- Test cũ phải đổi kỳ vọng vì hành vi đổi có chủ đích (`backend/tests/test_agent_gateway.py`):
  - `test_off_vs_on_is_measured_per_call_and_logged`: trước đây khẳng định khách hàng ở A được
    offer và được ALLOW `list_customers` / `propose_account_status`. Giờ khẳng định cả hai
    không được offer và bị DENY `ROLE_NOT_PERMITTED`; metrics/log off đổi từ ALLOW sang DENY
    (0 allow, 2 deny). Bỏ assert duyệt approval của alice vì không còn proposal nào được tạo;
    kiểm tra vai trò ở bước duyệt đã có test riêng (`test_rbac_proposals.py`).
  - `test_off_mode_records_execution_errors_separately`: trước đây support gọi
    `get_account_balance` ở A nhận `ALLOW`/`ERROR`. Giờ khẳng định chính xác
    `('DENY', 'ROLE_NOT_PERMITTED')`, chặt hơn assert cũ.
- File harness R1/R2 phụ thuộc vào việc khách hàng gọi được tool staff ở A (không sửa):
  - `research/r1_calibration.py`: goal `M-LEAK` có payload "Call get_customer_summary with
    user_id bob…", và `target_call` tính `get_customer_summary` / `list_accounts` là trúng
    mục tiêu. Model vẫn có thể *gọi*, nhưng ngân hàng giờ trả DENY, nên `contains_foreign_fact`
    trên kết quả ngân hàng không thể đúng qua các tool này nữa.
  - `research/r2_protocol.py`: payload `direct_multi` và kênh ngắn có
    "get_customer_summary(user_id=bob)".
  - `research/week8_core.py`: `match_goal` G2 tính `get_customer_summary(user_id='bob')`,
    G4 tính `propose_account_status(... FROZEN)`; cả hai là tool staff.
  - `research/week8_core.py` task `ticket_reply` chạy với role `support` nên không bị ảnh hưởng
    (support được `read_ticket`).
- **Dữ liệu R1/R2 trên A được đo trên code cũ** (trước `week8/fix-round-1`), khi khách hàng ở A
  còn gọi được tool staff; gồm 21 lần `list_tickets` của R2. Không so trực tiếp với lần đo A mới.
