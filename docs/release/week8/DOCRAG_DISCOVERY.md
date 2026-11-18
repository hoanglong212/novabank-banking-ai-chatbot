# Document RAG — Phase 0 discovery

Ngày khảo sát: 2026-11-18. Baseline: `099577fdd7d7f79a529c326ef1153095718e307a` (main sau PR #7). Nhánh: `feature/document-rag`.

**Trạng thái tại Phase 0:** đã khảo sát và lập bản đồ; lúc đó chưa viết code tính năng và đã dừng để báo các khác biệt thiết kế. Sau đó người dùng yêu cầu tự nghiên cứu, giải quyết và làm đến khi xong, giữ nguyên design system. Các quyết định triển khai được ghi trong `docs/plans/DOCUMENT_RAG_IMPLEMENTATION.md`; kết quả thực thi nằm ở `FUNC_API_TEST_REPORT.md`. Discovery này giữ lại bằng chứng lịch sử, không phải kết luận kiểm thử.

## 1. Nguồn đã đọc

- Toàn bộ kế hoạch Document RAG người dùng đính kèm ngày 2026-11-18.
- `C:/Users/Admin/Downloads/NovaBank_Kien_truc_theo_tang.pdf`, 9 trang, trạng thái tài liệu 2026-11-17. SHA-256: `611de23443ac88c15d0e1ed9b56647ee945479e40de272118b49917daf0bca31`. Đọc toàn bộ text bằng Poppler và render/kiểm tra sơ đồ trang 2.
- Code ở baseline trên, các policy A–D, workflow CI và harness hiện có.
- Chưa tìm thấy `AGENT_TEST_PLAN_FUNC_API.md` trong repo, Downloads, Documents, thư mục attachments và OneDrive/Documents đã tìm. Các tài liệu có sẵn gồm `docs/release/TEST_PLAN.md`, `PI_TEST_PLAN.md` và báo cáo pentest local; không tự coi chúng là bản thay thế.

## 2. Ánh xạ tầng → code thật

| Tầng | Thành phần | File và hàm thật |
|---|---|---|
| 0a | Input guard | `backend/app/agent/guard.py::inspect_prompt`, `redact_secrets`; được gọi ở `backend/app/routes_agent.py::stream` và `backend/app/agent/agent_access.py::create_run` |
| 0b | Chốt ý định | `backend/app/banking_workflow.py::bind_request`; `backend/app/agent/agent_access.py::permitted_tools`, `create_run`, `intent_hash`, `authenticate`, `context` |
| 0b | Capability token | `create_run` phát JWT audience `novabank-agent-tools`, `sub/sid/ver/run/tools/intent`, hạn 180 giây; `routes_agent.py::delegated` gọi `authenticate` |
| 1a | FIELD_TRUST, nhãn và T4-bind | `backend/app/agent/provenance.py::FIELD_TRUST`, `observe`, `inherited_label`, `inherit`, `user_value`, `validate`; gọi từ `execute_tool` và `bound_proposal` |
| 1b | Source screening | `backend/app/agent/source_screen.py::classify` → regex/input guard → `promptguard.py::classify` → `agent_guard.py::classify` |
| 1c | Cách ly nguồn | `backend/app/agent/quarantine.py::source_id`, `filtered`, `halt`; API xem cách ly ở `backend/app/routes_quarantine.py` |
| 2 | Datamarking | `agent_service/spotlighting.py::FIELD_TRUST`, `Spotlighter.transform`, `for_context`; tích hợp trong `agent_service/main.py::run_events` |
| P | Pseudonymizer | `backend/app/agent/guard.py::Pseudonymizer`; `agent_access.py::vault_for`, `private_text`, `trace_safe`; mã hóa vault bằng `backend/app/auth_crypto.py` |
| 3 | Gateway | `backend/app/routes_agent.py::tool` → `backend/app/agent/agent_access.py::execute_tool`; đề xuất ghi đi qua `bound_proposal` |
| 3 | JSON policy | `backend/app/agent/policy.py::load`, `evaluate`, `layer_enabled`; `backend/app/agent/policies/{A,B,C,D}.json` |
| 3 | Rủi ro | `backend/app/risk/scorer.py::score`, `prepare`, `observe`; lưu case ở `backend/app/risk/cases.py` |
| 4 | Duyệt và xác minh | `agent_access.py::approve`, `backend/app/transfers.py`, `transfer_stepup.py`, `transfer_token.py`, `action_security.py` |
| 5 | Lọc đầu ra | `backend/app/agent_output.py::filtered_answer`, `_filtered_answer`, `cite_retrieved_sources`; `backend/app/agent/disclosure.py::minimize`, `filter_answer`, `financial_classes` |
| 6 | Security events | `backend/app/security_events.py::emit`, `safe`, `output`, `ladder` |
| T | Dual LLM ticket | `backend/app/agent/quarantined_llm.py::isolate_ticket`, `_request`, `validate_classification`, `main_result`; lưu kết quả dành cho người ở `ticket_isolation.py::save`, `human_view` |

`backend/app/guard.py` và `backend/app/agent_access.py` là compatibility alias; implementation thực nằm dưới `backend/app/agent/`. Không tạo một implementation thứ hai ở các file alias.

## 3. Đường đi đầy đủ của tool ticket

### 3.1 Từ model đến Bank API

1. Bank API tạo run sau khi xác thực user và quyền sở hữu conversation; chốt ý định trước khi đọc nguồn, tạo vault, cấp delegated token.
2. Agent service lấy `/api/agent/context`. `agent_service/main.py` gọi Ollama và chuyển mọi tool call tới `POST /api/agent/tools` bằng delegated token. Agent không tự query DB.
3. `routes_agent.delegated` xác thực token/run/session; `routes_agent.tool` gọi `execute_tool`.
4. Thứ tự thực tế trong `execute_tool`: trạng thái app/run/session và ngân sách → tên tool hợp lệ → **vai trò** → **tool trong token nếu intent_binding bật** → hash ý định cho tool ghi → permitted_tools → giải mã pseudonym và validate schema → dispatch. Thứ tự này khác thứ tự role/token trong PDF và bất biến 2 của kế hoạch.
5. `staff_tools.execute` đọc `read_ticket` với RBAC đã được kiểm ở gateway; kiểm ticket_id có trong yêu cầu khi binding bật; lấy subject/description/messages và các bank facts. Đây là tool nhân viên có quyền đọc ticket theo vai trò, **không phải mẫu ownership customer** để sao chép nguyên SQL cho tài liệu cá nhân.

### 3.2 Xử lý kết quả ở Bank API

1. Nếu bật quarantine: `quarantine.filtered` loại nguồn đã cách ly.
2. `provenance.observe` đọc `FIELD_TRUST`, ghi source IDs/hashes, nâng nhãn lên UNTRUSTED. Việc quan sát nhãn hiện chạy cả khi enforcement provenance tắt; enforcement T4-bind mới theo layer flag.
3. Nếu bật output_filter: `disclosure.minimize` giảm các trường dữ liệu theo vai trò/ý định.
4. `safe_result = private_text(vault, result)` thực hiện P **trước** các model phân loại và model cách ly.
5. Ở B/D, `source_screen.classify` kiểm JSON của safe_result; không kiểm từng chunk độc lập vì ticket chưa có khái niệm chunk. Lỗi detector đóng đường đọc với `SOURCE_GUARD_UNAVAILABLE`, khác nguồn độc `SOURCE_INJECTION`.
6. Ở C/D, `read_ticket` được đưa vào `isolate_ticket(safe_result, role=...)` nếu vẫn ALLOW và chưa cách ly. `_request` lấy phần subject/description/body có giới hạn từ dữ liệu đã pseudonymize, gọi Ollama `/api/chat`, `tools=[]`, JSON schema chặt, timeout có giới hạn.
7. Bank API validate output; chỉ `category`, `urgency`, `mentions_instruction`, các enum/trường số bank-owned được đưa lại cho model chính. `summary` là **human-only**, được mã hóa vào `ticket_assessments`; không truyền vào tool context. Lỗi model/schema trả unreadable, không fallback sang prose.
8. Gateway lưu kết quả/trace đã mask, vault mã hóa và security events; áp dụng halt/quarantine khi cần. Sau đó trả HTTP tool result về Agent service.

### 3.3 Tới model chính

- **A:** không classifier/quarantine enforcement/Dual LLM/spotlighting; prose ticket đi qua P rồi vào model chính. RBAC, ownership ở API phù hợp, duyệt/xác minh ngân hàng vẫn còn.
- **B:** có classifier và quarantine; nếu nguồn được cho qua, prose đã qua P được datamarking theo field rồi bọc `<untrusted_tool_data>` và đưa vào model chính. B không chỉ có spotlighting.
- **C:** không source classifier/spotlighting; có Dual LLM, binding, provenance và output filter. Main chỉ nhận phần cấu trúc cho phép từ ticket.
- **D:** classifier + quarantine + Dual LLM + binding/provenance/output filter + spotlighting.

**Tiến trình:** client điều phối isolated model nằm trong **Bank API**, không phải Agent service. Inference vẫn chạy trong tiến trình **Ollama** qua HTTP. Isolated model không nhận tool schemas hay quyền DB; đầu vào của nó đã qua P. Main model được Agent service điều phối qua Ollama.

**Khác biệt có chủ đích trong kế hoạch RAG:** `answer` dài tối đa 500 ký tự vẫn là free text, khác ticket vốn không đưa summary sang main. Schema/citation validation không biến answer thành TRUSTED; vẫn phải đưa trường này vào FIELD_TRUST và P/spotlighting. Không mô tả RAG là bảo đảm "không có kênh prose" như ticket.

## 4. Route, DB, model và kiểm thử hiện có

### Route và migration

- FastAPI `backend/app/main.py::create_app` đăng ký router; ví dụ `routes_agent.py` dùng `APIRouter(prefix='/api')`.
- `dependencies.current_user` → `auth.authenticate`; `customer_user` yêu cầu `banking:own`; `get_db` lấy DB từ config phía server. Routes tài liệu cần lấy owner từ principal, không từ form/tool args.
- `Database.connect` bật foreign keys và busy timeout. `Database.initialize` gọi các hàm migration theo version trong `schema_migrations`; các module mới có `initialize(conn, stamp)` idempotent. Version cao nhất trong chuỗi hiện tại là 20 (`transfer_source.py`). Chưa tạo migration 21.
- `identity.transaction` là transaction helper hiện có; repo tài liệu phải tập trung toàn bộ SQL dữ liệu documents/chunks và owner filter. Không sao chép khả năng đọc ticket của staff thành khả năng đọc tài liệu khác chủ.

### Ollama và dependency

- Main model: `agent_service/main.py`, Ollama `/api/chat`, messages/tools do Bank API cung cấp.
- Isolated ticket: `quarantined_llm._request`; source detector: `agent_guard.model_request`/`classify`. Các endpoint/model lấy từ config phía server.
- Chưa có đường embedding `nomic-embed-text` cho tài liệu trong flow này; cần kiểm tra model local khi triển khai, không tự tải model.
- Venv backend hiện có `numpy`, `reportlab`; không có `pypdf`, `python_multipart` hoặc `multipart`. requirements backend chưa khai báo pypdf/numpy/python-multipart trực tiếp.
- Kế hoạch cho phép pypdf/numpy nhưng yêu cầu hỏi trước dependency khác. Đề xuất xin phép **python-multipart** để dùng parser multipart chuẩn của FastAPI; không tự viết parser thay thế để lách giới hạn dependency. Chưa cài hoặc sửa requirements.

### Test và harness

Các lệnh dưới đây là inventory từ code/workflow, không phải kết quả chạy lại ở Phase 0:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests research/tests -q --tb=short
& backend/.venv/Scripts/python.exe -m ruff check backend/app agent_service research scripts tools
& backend/.venv/Scripts/python.exe -m compileall -q backend/app agent_service research scripts
& backend/.venv/Scripts/python.exe scripts/financial-coverage.py
npm.cmd run test:components --prefix frontend
# Chạy trong frontend: npm.cmd run test:e2e
```

- `.github/workflows/checks.yml` chạy lint Python/JS, compileall, backend financial coverage, research tests, component checks, build và Playwright E2E. Chưa có lệnh hợp nhất Document RAG/JUnit/HTML.
- `scripts/seed_realistic.py --output <NEW_DISPOSABLE_DB> --seed 20261115` tạo DB mới, từ chối ghi đè, dùng seed/anchor cố định, xác minh ledger và FK, có business fingerprint. Security salts cố ý ngẫu nhiên: so fingerprint dữ liệu nghiệp vụ, không so byte toàn bộ DB. Test: `backend/tests/test_realistic_seed.py`.
- Pentest A–J hiện nằm ở **ignored** `.local/week8-pentest/`: `llm_attacks.py A B C D`, `e_injection.py`, `week7.py`, `deterministic.py`, `g8.py`, `extras.py`, `positives.py`, `positives2.py`, `report.py`; `W8_CONFIG=A|D` chọn cấu hình. `run_chain.sh`/`post2.sh` ghi lại các bước chạy thực tế.
- Ví dụ entry point hiện có: `$env:W8_CONFIG='D'; & backend/.venv/Scripts/python.exe .local/week8-pentest/llm_attacks.py A B C D`. Các chữ A–D cuối lệnh là **nhóm tấn công**, không phải cấu hình; cấu hình lấy từ environment.
- Harness này hardcode demo `http://127.0.0.1:8080` và DB/log `.local/local-deploy/novabank-realistic.sqlite3`. **Chưa chạy**, vì nó thay đổi DB demo/cấu hình và ghi đè kết quả cũ. Cần đóng gói bản chạy trên DB disposable, lưu evidence riêng và giữ baseline trước khi đo hồi quy.
- Benign utility đã có `scripts/week8-promptguard-utility.py` → `research/promptguard_utility.py`, hỗ trợ config B/C/D; không mặc nhiên coi đó là phép đo A đầy đủ. Harness ma trận `scripts/week8_evaluate.py` hỗ trợ A/B/C/D, mặc định chỉ lập kế hoạch, `--execute` mới chạy disposable services/inference. Cần đối chiếu protocol và baseline trước khi chọn phép so sánh, không lấy mock làm số liệu live.

## 5. Khác biệt ảnh hưởng thiết kế và điểm cần quyết định

| ID | Bằng chứng hiện tại | Tác động / đề xuất chưa thực hiện |
|---|---|---|
| D1 | `execute_tool` kiểm role trước token-tool, khác PDF trang 6 và bất biến 2 | Đề xuất giữ thứ tự code hiện có để không đổi gateway/hồi quy; xin chấp thuận điều chỉnh mô tả bất biến. Nếu phải theo PDF thì đó là thay đổi gateway cần phê duyệt rõ. |
| D2 | `policy.evaluate` chỉ được gọi trong `bound_proposal`; tool đọc dispatch trực tiếp. Cả A–D có catch-all rule. | Chỉ thêm rule ask_document sẽ không bảo đảm thiếu rule → NO_MATCHING_POLICY. Đề xuất enforcement riêng cho read tool mới trong execute_tool, yêu cầu rule khớp tường minh, giữ nguyên semantics tool cũ; cần chốt vì thay đổi đường kiểm policy của read tool. |
| D3 | `security_events.output` lưu raw/filtered đã mask; `tool_called` lưu arguments; `agent_calls.result_json` lưu tool results đã mask. | Mask PII không đồng nghĩa loại nội dung tài liệu. RAG không thể sao chép nguyên logging của ticket. Cần tách payload model khỏi audit payload, chỉ id/hash/rule_id cho dữ liệu tài liệu, gồm nhánh output-filter; không đưa tài liệu thô vào trace/harness log. |
| D4 | `Pseudonymizer.restore` đổi mọi alias có trong vault; create_run cấp alias tài khoản trước khi đọc nguồn. | `<ACCOUNT_1>` do tài liệu tự viết có thể đụng alias đã cấp. PDF chỉ bảo đảm cho mã *chưa được vault cấp*, yếu hơn kỳ vọng tuyệt đối của fixture DOC-SEC-03. Đề xuất vô hiệu literal alias có sẵn trong tài liệu trước P, không thay đổi toàn bộ vault của tool cũ; cần chốt trước triển khai. |
| D5 | Classifier bật B/D, tắt A/C; intent_binding bật C/D, tắt A/B | Giữ ablation hiện có. Ingest luôn screen theo yêu cầu kế hoạch là ranh giới upload mới, không suy diễn thành bật classifier toàn cục ở A/C; read-only capability guarantee phải ghi rõ cấu hình. Không thu hẹp toàn bộ A/B làm mất đối chứng. |
| D6 | Ticket main_result không có prose; RAG schema có answer | Sự khác biệt đã được yêu cầu rõ ở Phase 3, không tự loại answer. Ghi giới hạn bảo đảm; mọi prose của document result vẫn UNTRUSTED. |
| D7 | FIELD_TRUST bank và agent không giống hệt; tên trường khác nhau ở knowledge/audit/read_ticket | Bổ sung các trường tài liệu ở cả hai registry, có coverage tests; không dùng một registry làm bằng chứng registry kia đã phủ đủ. |
| D8 | Không có multipart parser trong môi trường; thiếu test plan được dẫn | Cần phép thêm python-multipart và vị trí/bản test plan chính thức trước khi chốt đầy đủ dependency/report contract. |

Các khác biệt trạng thái khác: PDF ghi fix-round-1 đang làm nhưng baseline hiện đã chứa các sửa role/disclosure/prompt/proxy; phần PIN trong PDF tự ghi là nhánh đang hoàn thiện. `transfer_stepup.py` hiện vẫn có recipient-bound step-up; không đổi chính sách này trong RAG. Nhãn được kế thừa theo **conversation_id**, không phải mọi conversation dùng chung auth session; tài liệu tính năng/test phải dùng đúng nghĩa đó.

### Probe chỉ đọc đã thực hiện

Không gọi model hoặc DB demo. Import code với `PYTHONPATH=backend`, truyền facts giả định cho policy.evaluate:

| Config | ask_document chưa đăng ký nhưng evaluate trả |
|---|---|
| A | allow / A-lab-control |
| B | approve_with_otp / B-bank-approval |
| C | approve_with_otp / bank-approval |
| D | approve_with_otp / bank-approval |

Đây là bằng chứng về **policy evaluator**, không phải gateway đã cho gọi tool chưa đăng ký (MODELS vẫn chặn). Probe vault với một tài khoản giả cho thấy literal ACCOUNT_1 được restore khi alias đã cấp; ACCOUNT_99 chưa cấp được giữ nguyên. Đây là discovery của helper hiện có, không phải kết quả chạy DOC-SEC trên tính năng chưa tồn tại.

## 6. Gate kết thúc Phase 0

- [x] Đã đọc kế hoạch và 9 trang kiến trúc; đối chiếu sơ đồ.
- [x] Bảng tầng có file/hàm thật; đường ticket A/B/C/D, nơi chạy model và P đã mô tả.
- [x] Route, session, migration, Ollama, test/harness và seed đã khảo sát.
- [x] Các sai khác và hướng xử lý đề xuất đã ghi; không tự thay đổi gateway, policy, P hoặc dependency.
- [ ] Chờ người dùng chốt D1/D2/D4 và cấp phép python-multipart; cung cấp vị trí test plan.
- [ ] Phase 1–6 chưa triển khai; chưa có kết quả RAG API/security/utility.

File pentest người dùng đang để untracked được giữ nguyên. Không commit `.local/`, DB, secrets hoặc evidence thô. Nhánh này chỉ kết thúc ở PR để nhóm review, không được merge tự động.
