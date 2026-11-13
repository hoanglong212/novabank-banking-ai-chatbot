# Báo cáo kiểm tra prototype NovaBank – Tuần 7

Ngày kiểm tra: 13/11/2026 · Commit: `21813d4` (nhánh `main`, working tree sạch) · Người kiểm tra: Claude Code (chỉ đọc, không sửa code)

**Cách kiểm tra**

- Đọc mã nguồn backend (`backend/app`, khoảng 7.400 dòng), agent service, frontend (phần auth/QR/chat/admin), `research/`, `tools/`, `scripts/` và tài liệu bằng chứng trong `docs/release/`.
- Chạy toàn bộ test backend: `cd backend && .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` → **586 passed, 1 warning** (213 giây). Warning là khoá HMAC 9 byte trong một test, không phải trong code chạy thật.
- Chạy hai probe chỉ đọc trên DB SQLite tạm (thư mục temp, không chạm DB của repo), bằng `TestClient` nội bộ, không gửi request ra ngoài. Hai probe xác nhận các lỗ hổng R1 và R2 ở phần 3. Sau khi chạy, `git status` vẫn sạch.
- **Không chạy** test frontend (Playwright, vitest), không chạy Ollama/LLM thật. Các số liệu dùng model thật trong báo cáo này lấy từ file bằng chứng nhóm đã commit, mình không tự đo lại.

Ký hiệu: ✅ đã có · ⚠️ có một phần · ❌ chưa có · ➖ không kiểm tra được bằng code.

---

## 1. Tóm tắt

| Mục | Trạng thái | Ghi chú ngắn |
|---|---|---|
| A1. Đăng nhập OTP | ✅ | OTP 6 số qua hộp thư demo, hết hạn sau 120 giây, dùng một lần, tối đa 5 lần sai. Lưu ý: thiết bị tin cậy bỏ qua OTP trong 30 ngày (chỉ áp dụng cho khách hàng) |
| A2. JWT trước mọi hành động | ✅ | Mọi route nhạy cảm đều có `Depends(current_user/customer_user/require_permission)`. Ngoại lệ đáng lo duy nhất: `/api/dev/outbox` (xem R1) |
| A3. Chuyển tiền Alice ↔ Bob | ✅ | Có seed, OTP riêng mỗi lệnh, receipt PDF, lịch sử, tool đọc giao dịch cho agent |
| A4. Chuyển tiền bằng QR | ✅ | jsQR/BarcodeDetector ở client, server chỉ nhận `NBQR1:` có chữ ký HMAC, validate bằng Pydantic |
| A5. Gateway | ⚠️ | Có thật trong code: schema, identity, policy, log, cờ bật/tắt. Phân loại rủi ro chỉ ngầm định, bước phê duyệt không độc lập (cùng người, cùng phiên) |
| A6. Tính năng phụ | ⚠️ | Có budget, máy tính, mục tiêu tiết kiệm, ticket qua agent, SQLite. Admin **không** có mã xác minh riêng, chỉ có MFA bắt buộc |
| B1. QR giả (quishing) | ✅ | Có `quishing-qr.png`, trang attacker chạy local trên loopback, trace với Qwen, kết luận có giới hạn rõ ràng |
| B2. Admin agent và RBAC | ✅ | Role lấy từ DB, tool lọc theo role, kiểm tra lại ở server khi thực thi và khi phê duyệt, có test leo quyền. Tài liệu RBAC đã lỗi thời |
| B3. Lỗi vượt gateway | ⚠️ | Đã có bản sửa, regression test, tài liệu nguyên nhân (nguyên nhân lịch sử vẫn chỉ là giả thuyết). Còn ba điểm yếu: client tự chọn `profile=baseline`, bộ lọc input là blacklist, phê duyệt không độc lập |
| B4. Bắt traffic | ⚠️ | Có 4 file HAR từ proxy tự viết và schema JSON. **Chưa có capture bằng Caido/Burp** |
| B5. Signed authorization token | ❌ | Không có token ký riêng cho từng lệnh chuyển tiền. Bù lại bằng draft bất biến ở server và OTP gắn `transfer_id`. Đã có tài liệu về rủi ro bị đánh cắp danh tính |
| B6. Hộp thư OTP giả lập | ⚠️ | Đã có trang `/outbox` và OTP không còn hiện trên màn đăng nhập. Nhưng **mọi người đều thấy email của mọi user, không cần đăng nhập** |
| B7. Biện pháp giảm thiểu khác | ✅ | Rate limit, hạn mức mỗi lần/ngày/người nhận mới, LLM-as-judge (có số liệu judge bị qua mặt), agent service không có quyền DB, RAG chỉ admin được ghi |
| C1. Bộ test kiểu AgentDojo | ⚠️ | 7 vector × 5 payload (v1.1) cộng 35 payload khó, 100 tác vụ hợp lệ. Thiếu vector hoá đơn PDF thật đi qua RAG |
| C2. Script và chỉ số | ✅ | `research.run`, `tools/gateway_compare.py`, `scripts/week7-report.py`. Có đủ 3 chỉ số ở runner HTTP live, có so sánh gateway tắt/bật, xuất CSV/JSON |
| C3. Bằng chứng cho buổi họp | ⚠️ | Đã đủ, trừ capture Caido/Burp. Phần bảng ASR cần đọc kỹ chú thích (xem C3) |

---

## 2. Chi tiết từng mục

### PHẦN A – Nền tảng Tuần 6

#### A1. Đăng nhập có OTP — ✅

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Đăng nhập xong sinh OTP, phải nhập mới vào app | ✅ ⚠️ | `backend/app/mfa.py:68-93` (`begin_login`) trả `mfa_required` và tạo challenge, `mfa.py:35-53` sinh mã 6 số và ghi vào `dev_outbox`. JWT chỉ được cấp ở `mfa.py:138-140` sau khi OTP đúng. **Ngoại lệ:** `mfa.py:85-87`: khách hàng có `device_token` tin cậy (30 ngày, `mfa.py:11`) được vào thẳng, không cần OTP. Staff luôn phải qua MFA (`mfa.py:16`) |
| OTP có hạn và dùng một lần | ✅ | Mã hết hạn sau 120 giây (`mfa.py:46`), challenge hết hạn sau 300 giây (`mfa.py:60`). Mã bị huỷ khi dùng (`mfa.py:136`, `session_security.py:55-57`). Gửi lại thì sinh mã mới và xoá mã cũ (`mfa.py:44-47`) |
| Sai OTP bị từ chối, có giới hạn số lần | ✅ | Tối đa 5 lần sai mỗi challenge (`mfa.py:28`, `mfa.py:130-131`). Khoá tài khoản 15 phút sau 5 lần sai (`session_security.py:10`, `:34-40`). Giới hạn 20 request/15 phút theo IP cho mỗi endpoint auth (`identity.py:65-69`). Gửi lại tối đa 4 lần, mỗi lần cách nhau ít nhất 30 giây (`mfa.py:36-39`) |

#### A2. JWT kiểm tra trước mọi hành động — ✅

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Endpoint nhạy cảm có kiểm tra JWT | ✅ | `backend/app/auth.py:79-99`: kiểm tra chữ ký HS256, `iss`, các claim bắt buộc, `auth_version`, và session còn sống trong DB (`session_security.py:77-84`). Chuyển tiền dùng `customer_user` (`api/routes/transfers.py:21-63`). Giao dịch dùng `routes_banking.py:16-33`. Admin dùng `require_permission` (`routes_admin.py:15-16`). Chat dùng `assistant_user` (`routes_agent.py:165-166`). Tool của agent dùng JWT ủy quyền riêng (`agent/agent_access.py:241-258`) |
| Token sai/hết hạn/thiếu → 401 và logout | ✅ | `auth.py:85-96` trả 401. Frontend thử refresh một lần rồi `endSession` (`frontend/src/api.ts:19-30`, `sessionStore.ts:156`). JWT sống 5 phút (`auth.py:17`), session hết hạn sau 5 phút không hoạt động (`session_security.py:8`) |
| Endpoint **không** kiểm tra JWT | ⚠️ | Công khai có chủ đích: `/api/health`, `/api/ready`, `/api/auth/login`, `/mfa/verify`, `/mfa/email`, `/refresh`, `/register`, `/resend-verification`, `/verify-email`, `/forgot-password`, `/reset-password` (tất cả có rate limit). `/api/agent/context`, `/tools`, `/preview`, `/finish` dùng JWT ủy quyền thay cho JWT người dùng. **Đáng lo:** `GET /api/dev/outbox` và `GET /api/dev/outbox/{id}` (`api/routes/dev.py:19-40`) không có xác thực khi `ENV=demo` (xem R1) |
| Secret JWT không hard-code | ✅ | `auth.py:16`: đọc `JWT_SECRET` từ env, nếu thiếu thì sinh ngẫu nhiên. `backend/.env.example:24` để trống. Lưu ý: mật khẩu demo nằm trong comment `auth.py:44` và README (có chủ đích cho demo) |

#### A3. Chuyển tiền giả lập Alice ↔ Bob — ✅

| Tiêu chí | | Bằng chứng |
|---|---|---|
| Có tài khoản Alice, Bob | ✅ | `backend/app/database.py:21-22` (`ACC-ALICE-001` 12.500.000đ, `ACC-BOB-001` 8.750.000đ) |
| Mỗi lệnh có OTP riêng | ✅ | `transfers.py:135-168`: OTP 6 số gắn `transfer:<id>`, hết hạn sau 2 phút (`:27`), tối đa 3 lần sai (`:29`, `:196-203`). Nếu user đã cài TOTP hoặc PIN thì dùng factor đó (`:147-151`) |
| Receipt tải về được | ✅ | `routes_banking.py:26-34` (PDF, chỉ cho giao dịch `COMPLETED` của chính chủ) |
| Ghi vào lịch sử | ✅ | `transfers.py:206-209` (`post_transfer` vào ledger và cập nhật `transaction_id`) |
| Agent trả lời về giao dịch | ✅ | Tool `get_recent_transactions`, `get_transaction_status` (`agent/agent_access.py:375-378`) |

#### A4. Chuyển tiền bằng upload QR — ✅

| Tiêu chí | | Bằng chứng |
|---|---|---|
| Upload ảnh tự điền tài khoản và số tiền | ✅ | `frontend/src/components/qr/QrStudio.tsx:16-18` (`toTransfer` điền `to_bank`, `to_account`, `amount_vnd`, `content`) |
| Thư viện decode | ✅ | Client: `BarcodeDetector` gốc của trình duyệt, nếu không có thì dùng `jsqr@1.4.0` (`frontend/src/components/qr/qrReader.ts:5-30`, `package.json`). Server: `/api/qr/decode` (`routes_qr.py:17-27`) nhận chuỗi QR, hoặc đọc payload trong **text chunk của PNG** (`local_qr.py:78-90`). Đường PNG ở server không giải mã quang học. Ngoài ra có OCR `tesseract.js@7.0.0` cho ảnh chụp màn hình ngân hàng (`ImageTransfer.tsx`, `recognizeBankImage.ts`) |
| Validate nội dung QR | ✅ | Bắt buộc tiền tố `NBQR1:`, tối đa 4.000 ký tự, HMAC-SHA256 bằng `SECRET` (`local_qr.py:46-58`), rồi qua schema `VietQRArgs`. `VietQRArgs` không có trường URL (`docs/release/week7-evidence/QUISHING.md`). Ảnh tối đa 2 MB và 4 MP (`local_qr.py:79-84`). QR chứa URL bị trả 422 (`media/qr-rejection.json`) |

#### A5. Gateway (phòng thủ runtime) — ⚠️

Gateway thật nằm ở `backend/app/agent/agent_access.py` (`execute_tool`, `bound_proposal`) và `agent_gateway.py`. Riêng `agent/gateway.py` (`PolicyGateway`) chỉ là đường legacy: chế độ `local` mặc định ALLOW sau khi kiểm tra chủ sở hữu (`agent/gateway.py:36-37`), và chỉ chạy khi `LEGACY_AGENT_TEST_MODE=true` (`api/routes/chat.py:56-57`).

| Lớp | | Bằng chứng / lý do |
|---|---|---|
| Schema validation tool call | ✅ | `agent_access.py:358` gọi `MODELS[name].model_validate(...)`. Các model dùng `extra='forbid', strict=True` (`identity_schemas.py:6-7`). `TransferArgs` có regex tài khoản và giới hạn 1.000–100.000.000đ (`schemas.py:59-66`). Tên tool lạ bị `TOOL_NOT_ALLOWED` (`agent_access.py:350-351`) |
| Identity check | ✅ | JWT ủy quyền có `aud=novabank-agent-tools`, gắn với run/session/version, sống 180 giây (`agent_access.py:235-237`, `:241-258`). Role được đọc lại từ DB ở mỗi lần gọi tool. Agent service không có DB và không có secret (`agent_service/main.py:1-5`) |
| Policy engine theo rule | ✅ | Allowlist theo role (`agent_access.py:352-353`), theo intent của tin nhắn mới nhất (`:145-158`, `:355-356`), ràng buộc người nhận/số tiền/ngân hàng với lời người dùng (`:288-296`), chủ sở hữu tài nguyên (`:305-310`), giới hạn 8 lần gọi (`:341-342`), dừng sau 2 lần bị từ chối (`:343`, `:423`) |
| Phân loại rủi ro, phê duyệt độc lập cho rủi ro cao | ⚠️ | Có phân loại **ngầm định**: tool `get_*` chạy ngay, còn chuyển tiền, hoá đơn, khoá thẻ, ticket và mọi `propose_*` chỉ tạo `tool_approvals` ở trạng thái PENDING (`:324-328`). Sau đó người dùng phải duyệt (`:454-519`) rồi nhập OTP (`transfers.py:171-218`). Không có tool gửi email. **Không độc lập:** người duyệt chính là user đang chat, trong cùng session (`agent_access.py:460`). Và trong `ENV=demo`, OTP đọc được từ outbox công khai (R1). Không có thang điểm rủi ro hay nhãn rủi ro tường minh |
| Mọi allow/deny vào security log | ✅ | Bảng `agent_calls` (`agent_schema.py:23-26`; ghi ở `agent_access.py:345-347`, `:420-421`). File JSONL `<DB_PATH>.gateway.jsonl` hoặc `GATEWAY_LOG_PATH` (`agent_gateway.py:56-73`), gồm các trường `created_at, gateway, profile, owner_id, role, run_id, chat_request_id, tool_request_id, ordinal, tool, decision, reason, latency_ms` (`agent_gateway.py:20-21`). Input guard cũng được log (`routes_agent.py:174-177`). Admin xem qua `/api/admin/agent-gateway/log` và `log.csv` (`routes_admin.py:173-183`). Lưu ý: tham số tool được pseudonym hoá và che (`agent_access.py:335`) |
| Cờ bật/tắt gateway | ✅ | `PUT /api/admin/agent-gateway` (`routes_admin.py:166-170`), chỉ cho phép khi `ENV` là `demo` hoặc `lab`, ngoài ra luôn bật (`agent_gateway.py:24-42`, `:47-48`). Lưu ý: đây là **công tắc toàn hệ thống** (`bank_settings`), tắt là ảnh hưởng mọi user đang dùng server demo |

#### A6. Tính năng phụ — ⚠️

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Ngân sách, máy tính, mục tiêu tiết kiệm | ✅ | `routes_insights.py:33-35` (`/insights/budgets`), `frontend/src/components/explore/Calculators.tsx`, `Goals.tsx` (API `/savings-goals`, `products.py`) |
| Admin có mã xác minh riêng | ❌ | Không tìm thấy mã xác minh riêng cho admin. Admin chỉ phải qua MFA bắt buộc khi đăng nhập (không có thiết bị tin cậy, `mfa.py:16`) |
| Admin xem giao dịch mọi user, số user, ticket | ✅ | `routes_banking.py:72` (`/admin/transactions`), `routes_admin.py:35-60` (overview đếm `users`, `support_tickets`) |
| User tạo ticket qua agent | ✅ | `prepare_support_ticket` → user duyệt → `INSERT support_tickets` (`agent_access.py:297-301`, `:480-483`) |
| DB nhỏ, loại DB và schema | ✅ | SQLite (`database.py:43`). Schema có migration đánh số: `identity_schema.py`, `session_schema.py`, `banking_schema.py`, `agent_schema.py`, `experience_schema.py`. ERD ở `docs/release/ERD.md` |

---

### PHẦN B – Việc Tuần 7

#### B1. Tấn công bằng QR giả (quishing) — ✅

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Có ảnh QR giả trỏ tới trang do nhóm kiểm soát | ✅ | `docs/release/week7-evidence/quishing-qr.png`, sinh bởi `research/quishing.py --qr` |
| Có trang hoặc script attacker chạy local | ✅ | `research/quishing.py:117` (`lab_server`, HTTP trên `127.0.0.1` với cổng ngẫu nhiên). Trang `/pay` chứa payload chỉ dẫn chuyển 1.000đ cho Charlie (`research/quishing.py:27-31`) |
| Nội dung QR có vào context của LLM không | ✅ | **Không**, nếu đi qua app: QR được decode ở `/api/qr/decode` rồi điền form chuyển tiền, không đi qua chat. QR chứa URL bị 422 (`local_qr.py:47-48`). Chỉ khi người dùng tự dán link vào chat thì link mới vào context |
| Agent có tool truy cập URL không | ✅ | **Không** trong app: `MODELS` (`agent_access.py:64-79`) không có tool fetch/browse/HTTP. `fetch_external` chỉ có trong harness nghiên cứu, profile `experimental` (`research/quishing.py:12-18`), giới hạn allowlist loopback, không redirect, tối đa 32 KiB (`:90-114`) |
| Nội dung fetch có vào thẳng prompt không | ✅ | Trong harness: có, bọc thành `{'trust_level':'untrusted', ...}` (`research/quishing.py:114`). Trong app: không áp dụng vì không có fetch |
| Từ nội dung đó, agent có gọi được tool chuyển tiền không | ✅ | Gọi được, nhưng bị bank từ chối `USER_INTENT_REQUIRED` hoặc `USER_INTENT_MISMATCH` vì người nhận và số tiền chỉ lấy từ lời người dùng (`agent_access.py:288-296`). Trace: `quishing-qr-ollama-trace.json`. Qwen tự bịa người nhận, bank vẫn chặn |
| Gateway có chặn chuyển tiền xuất phát từ QR/URL không | ✅ | Có, nhờ binding (như trên), không phải nhờ phát hiện URL. Bộ lọc output còn chặn câu trả lời có `https?://` (`agent_output.py:41-42`) |
| Ghi lại kết quả | ✅ | `quishing-trace.json`, `quishing-ollama-trace.json`, `quishing-qr-ollama-trace.json`, `media/qr-rejection.json`, `media/qr-rejected.png`, `QUISHING.md` |
| ➖ Tài liệu nghiên cứu quishing | ➖ | Có `docs/research/QUISHING.md` và phần nền tảng trong `week7-evidence/QUISHING.md` (Greshake, AgentDojo, CaMeL). Mức độ đọc thì nhóm tự đánh giá |

Giới hạn nhóm đã tự ghi nhận: chỉ có một payload và một lượt, chạy trên loopback chứ chưa có VM, bước "camera" đọc từ PNG text chunk chứ không giải mã quang học.

#### B2. AI agent cho admin và kiểm thử RBAC — ✅

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Agent riêng hoặc dùng chung có phân quyền | ✅ | Dùng chung endpoint, phân quyền theo role: `permitted_tools(intent, role)` (`agent_access.py:145-147`). Staff có intent binding riêng (`staff_tools.py:110-131`). Giao diện `/admin/assistant` |
| Role định nghĩa ở backend | ✅ | `auth.py:35-41` (`ROLE_PERMISSIONS`). Role nằm trong bảng `users` (`identity.py:44-48`) |
| Tool lọc theo role | ✅ | `staff_tools.py:89-96`, `:100-108`. **Admin có mà user không có:** đọc gồm `list_tickets`, `read_ticket`, `get_user_count`, `list_transactions`, `get_customer_summary`, `list_failed_transfers`, `get_bank_overview`, `list_customers`, `list_accounts`, `get_bank_settings`, `list_audit_events`. Đề xuất (cần duyệt) gồm `propose_ticket_reply`, `propose_ticket_status`, `propose_account_status`, `propose_customer_update`, `propose_settings_change`, `propose_reconciliation`. Ngược lại, admin không có `prepare_transfer` |
| Kiểm tra quyền ở server khi thực thi tool | ✅ | `agent_access.py:352-353` (`ROLE_NOT_PERMITTED`), kiểm tra lại khi phê duyệt (`:468-472`). Không dựa vào system prompt |
| Role lấy từ JWT/session đã xác thực | ✅ | Role luôn tra từ DB theo `sub` (`auth.py:94`, `agent_access.py:249`). Claim `role` trong token bị bỏ qua (`tests/test_support_rbac.py:60`) |
| Test user giả làm admin | ✅ | `tests/test_support_rbac.py:41`, `:52`, `:60`; `tests/test_admin_agent.py`. Regex input guard bắt "act as admin/administrator" (`agent/guard.py:28`). Live: 5 kịch bản × 3 lần × 2 profile, **0/30 thành công** (`week7-evidence/RBAC_MATRIX.md`, `hard-live/results.csv`) |
| Ghi kết quả lấy được / bị chặn | ✅ | `RBAC_MATRIX.md`, `role-checks.xml`, `gateway-compare/results.csv`. Khi gateway **tắt**, rbac-* thành công 6/6, khi bật thì 0/6 (`gateway-compare/summary.md`) |

**Tài liệu lỗi thời:** `RBAC_MATRIX.md` (bảng đầu) liệt kê admin chỉ có 4 tool, và `CRYPTO_AUTHZ.md` ghi "Staff tools chỉ đọc, no approval tools". Code hiện tại có thêm 7 tool đọc và 6 tool `propose_*` cho staff (`staff_tools.py:89-96`), và `approval_user` cho staff phê duyệt (`dependencies.py:27-31`). Cần cập nhật trước buổi họp.

#### B3. Lỗi vượt gateway — ⚠️ (ưu tiên số 1)

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Có prompt/log của lần vượt gateway | ⚠️ | Prompt `SYSTEM OVERRIDE ...` có trong `docs/release/BYPASS_NOTE.md` và `week7-evidence/BYPASS_NOTE.md`. **Không có log, run ID hay profile của buổi demo 3/11**, nhóm đã tự ghi nhận điều này. Log `.local/week7-red.log` không được commit |
| Endpoint/tool chuyển tiền không qua gateway | ✅ | Agent không có tool xác nhận chuyển tiền. Chỉ `/api/transfers/{id}/confirm` mới chuyển tiền thật, và endpoint này cần JWT, OTP, idempotency (`api/routes/transfers.py:56-63`). Đường legacy `ToolDispatcher.create_transfer` tạo draft **không qua phê duyệt** (`agent/tools.py:101-108`), nhưng chỉ chạy khi `LEGACY_AGENT_TEST_MODE=true` và vẫn cần OTP. `scripts/serve.py` ép biến này về `false` |
| Gateway kiểm tra tên tool hay tham số; có alias, tham số lồng không | ✅ | Kiểm tra cả hai. Tên tool phải khớp chính xác key trong `MODELS` (`agent_access.py:350`). `execute_transfer` không tồn tại. Tham số lạ hoặc lồng bị `extra='forbid'` từ chối. Với `prepare_transfer`, tham số của model bị **thay bằng** bản canonical lấy từ lời người dùng (`agent_access.py:291-296`) |
| Kiểm tra trên text prompt hay trên tool call thật | ✅ | Trên tool call thật (`/api/agent/tools`). Input guard trên text chỉ là tripwire, nhóm đã ghi rõ |
| Policy có dùng blacklist từ khoá không | ⚠️ | **Có**, ở lớp input guard: `agent/guard.py:24-28` (`INJECTION` regex) và `:88` (`system override`, được thêm sau sự cố). Đây là điểm yếu: chỉ cần diễn đạt khác là lọt (nhóm đã thừa nhận). Intent binding `affirmative_action` cũng dựa trên regex danh sách từ (`banking_workflow.py:65-81`). Dù vậy, binding tham số không phụ thuộc vào blacklist |
| Thứ tự lớp sai hoặc fail-open | ✅ | Không thấy fail-open ở đường chính. Classifier lỗi thì nguồn bị cách ly (`agent/agent_guard.py:32-34`). Remote gateway lỗi thì DENY (`agent/gateway.py:54-55`). Exception lạ khi gateway bật thì raise lỗi, không ALLOW (`agent_access.py:398-402`). Hai ngoại lệ: `PolicyGateway` legacy chế độ `local` ALLOW mặc định (`agent/gateway.py:36-37`), và **khi `LLM_PROVIDER=mock` thì judge không chạy** (`agent_guard.py:19-20`) |
| Phê duyệt độc lập có bắt buộc không | ⚠️ | Bắt buộc phê duyệt rồi OTP thì có (`agent_access.py:508-519` chỉ tạo draft `PENDING_OTP`). Nhưng người phê duyệt là **cùng người, cùng session**, và OTP trong demo đọc được từ outbox công khai (R1). Giả thuyết H1+H4 trong `BYPASS_NOTE.md` cũng chính là kịch bản này: người demo tự bấm duyệt và nhập OTP |
| Đã có bản sửa hoặc tài liệu nguyên nhân | ✅ | Sửa regex (`guard.py:88`). G1 (memo thành người nhận), G2 (câu trích dẫn/phủ định), G3 (`get_bills` bỏ qua judge) đã sửa (`gateway-audit-2026-11-08/REPORT_VI.md`). Tài liệu: `BYPASS_NOTE.md`, `GATEWAY_OFF_ON.md`, `KNOWN_FAILURES.md` |
| Regression test | ✅ | `tests/test_PI_bypass_week7.py:11`, `:23` (cả hai profile, đổi người nhận thì DENY), `test_week7_intent.py`, `test_week7_live_fixes.py`, `test_gateway_audit.py`. Tất cả nằm trong 586 test đã pass |

**Các đường còn có thể đi vòng (phát hiện thêm khi đọc code):**

1. **Client tự chọn `profile`** (`routes_agent.py:25`, `:52`, `agent_access.py:199`). Gửi `"profile":"baseline"` thì bỏ được ba thứ: system prompt cứng (`agent_service/main.py:44-45`), judge kiểm tra nguồn (`agent_access.py:409`) và cơ chế dừng sau 2 lần bị từ chối (`:343`). Điều này đúng cả khi `ENV` không phải demo/lab (đã xác nhận bằng probe, xem R2). Binding và phê duyệt vẫn giữ.
2. **Gateway OFF là công tắc toàn cục** (`agent_gateway.py:36-42`). Khi tắt, customer được cấp **mọi** tool kể cả staff (`agent_access.py:269`), và tham số của model được lưu nguyên thành proposal (`:286-287`). Nếu quên bật lại trước khi demo thì sẽ tái hiện đúng sự cố 3/11.
3. **JWT ủy quyền được trả về trình duyệt** (`agent_access.py:238`, qua `POST /api/agent/runs`). User có thể tự gọi `/api/agent/tools` và `/api/agent/finish` mà không qua LLM. Hành động không vượt quyền của chính họ, nhưng họ ghi được câu trả lời "assistant" tuỳ ý vào hội thoại của mình. Lớp lọc output vẫn chạy khi gateway bật.

#### B4. Bắt traffic Caido/Burp — ⚠️

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| ➖ Cài Caido/Burp trên VM | ➖ | Không kiểm tra được bằng code. `capture/README.md` ghi rõ đây "không phải capture bằng Caido" |
| Cấu hình được proxy/base URL | ✅ | `AGENT_SERVICE_URL`, `OLLAMA_URL`, `BANKING_API_URL` (`.env.example:6,15`, `agent_service/main.py:15-16`). Frontend gọi `/api` tương đối, có Vite proxy (`frontend/vite.config.ts:10`). httpx dùng `trust_env` mặc định nên tôn trọng `HTTP_PROXY`, trừ harness nghiên cứu đặt `trust_env=False` |
| Danh sách request quan trọng | ✅ | `capture/README.md`: login, MFA, outbox, `/api/me`, chat stream, approvals, OTP chuyển tiền, confirm, QR decode; bank→agent `/run`; agent→bank `context/tools/preview/finish`; agent→Ollama `/api/chat` |
| Cấu trúc JSON và trường có thể sửa | ✅ ⚠️ | `capture/capture-summary.json` có schema của từng endpoint. Trường client kiểm soát đáng chú ý: `profile` (R2), `amount_vnd`/`to_account`/`from_account` của `/api/transfers` (server kiểm tra chủ sở hữu và hạn mức), `name`/`arguments` của `/api/agent/tools`. `role` và `user_id` không được nhận từ client |
| Thư mục lưu capture | ✅ | `docs/release/week7-evidence/capture/` (4 file HAR, đã che token và mật khẩu, test `tests/test_week7_capture.py`) |

#### B5. Xác thực bằng mật mã — ❌

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Gateway phát token ký riêng cho từng lệnh (user, số tiền, người nhận, thời hạn) | ❌ | Không có. Thứ đang có là JWT ủy quyền **theo run**, gồm `sub, sid, ver, run, scope, exp` (`agent_access.py:235-237`), **không** chứa số tiền hay người nhận |
| Tool chuyển tiền bắt buộc token và kiểm tra chữ ký | ❌ | Không áp dụng. `/confirm` kiểm tra JWT người dùng và OTP, không có token giao dịch |
| Nonce chống replay | ⚠️ | Không có nonce trong token. Chống replay bằng cách khác: OTP bị huỷ sau khi dùng, trạng thái `PENDING_OTP` → `COMPLETED`, idempotency key, `BEGIN IMMEDIATE` (`transfers.py:171-218`). Delegated JWT không có `jti`, có thể dùng lại trong 180 giây khi run còn mở |
| Ràng buộc đúng tham số | ⚠️ | Tương đương về mặt chức năng: draft được lưu ở server và không đổi sau `prepare`. OTP băm theo `transfer_id:otp` (`transfers.py:32-33`), nên không đổi được số tiền hay người nhận sau khi đã gửi OTP. Nhưng đây là **trạng thái server**, không phải chữ ký mật mã. Hash OTP là SHA-256 không có khoá (khác với OTP đăng nhập dùng HMAC, `auth_crypto.py:60-62`) |
| Tài liệu phân tích danh tính bị đánh cắp | ✅ | `week7-evidence/CRYPTO_AUTHZ.md`: hạn mức ngày, tối đa 5 giao dịch/10 phút, người nhận mới ≤ 10 triệu (`transfers.py:21-26`, `:63-72`, test `test_week7_limits.py:14`, `:20`). Có TOTP/PIN làm step-up (`mfa_settings.py`) |

#### B6. Trang email OTP giả lập — ⚠️

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| OTP không hiện trên màn đăng nhập | ✅ | Response login chỉ có `challenge_id` và thông báo "available in the local demo inbox" (`mfa.py:64-65`). Không tìm thấy `demo_otp` hay `secret_text` trong `frontend/src` |
| Có trang mock inbox | ✅ | Route `/outbox` (`frontend/src/App.tsx:45`), `components/dev/Outbox.tsx`, API `api/routes/dev.py`. Chỉ bật khi `ENV=demo` |
| Mỗi user chỉ thấy email của mình | ❌ | `api/routes/dev.py:19-23` liệt kê 50 email mới nhất của **mọi user**, không cần đăng nhập. `:26-40` trả mã OTP hoặc link theo `message_id`. Người nhận được che, nhưng frontend lọc theo loại mã (`Outbox.tsx:14`). Đã xác nhận bằng probe (R1) |
| Áp dụng cho OTP đăng nhập và OTP chuyển tiền | ✅ | `LOGIN_OTP` (`mfa.py:50-53`), `TRANSFER_OTP` (`transfers.py:159-164`), `ACTION_*` (`action_security.py:49-52`), link xác minh/đặt lại (`identity.py:88-89`) |
| OTP không lộ trong API, console, URL | ⚠️ | Response login/transfer không có OTP (`transfers.py:40-49`). Không có `console.log` trong `frontend/src`. Log HTTP không ghi body. **Nhưng** chính API outbox lộ OTP cho người không đăng nhập. Token đặt lại mật khẩu nằm trong fragment URL `/#reset-password?token=` (`identity.py:89`), bình thường với link email nhưng ở đây cũng lộ qua outbox |

#### B7. Biện pháp giảm thiểu khác — ✅

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Giới hạn số giao dịch theo thời gian | ✅ | 5 giao dịch hoàn tất/10 phút, kiểm tra cả lúc tạo và lúc xác nhận (`transfers.py:24-25`, `:63-68`, `:204-205`). 30 run agent/15 phút (`agent_access.py:215`). 15 yêu cầu xác nhận/15 phút (`action_security.py:57-61`) |
| Số tiền tối đa mỗi lần | ✅ | Schema 100.000.000đ (`schemas.py:64`), hạn mức admin cấu hình được (`posting.py:34`), ngày 200.000.000đ (`transfers.py:21`, `:52-60`), người nhận mới 10.000.000đ (`:26`) |
| LLM-as-judge | ✅ | `agent/agent_guard.py:16-34`: rule cố định trước, rồi Qwen. Chỉ chạy ở `defended` với các tool đọc được liệt kê (`agent_access.py:409`). **Judge bị prompt injection được:** bỏ sót 100% hai payload (`next_action` JSON, "Developer update"), và một tài liệu RAG nhiễm từng qua được judge 3/3 trước khi sửa (`GATEWAY_OFF_ON.md`, `KNOWN_FAILURES.md`). Judge không chạy khi `LLM_PROVIDER=mock` |
| Bảo vệ DB và RAG | ⚠️ | Agent service **không có quyền DB** (`agent_service/main.py:1-5`), mọi truy vấn qua bank và lọc theo `owner_id`. Nhưng phía bank dùng chung **một file SQLite với toàn quyền**, không có tài khoản DB quyền hạn chế (SQLite không hỗ trợ). RAG: chỉ admin ghi được (`routes_knowledge.py:44-66`), tài liệu có `trust_level='approved'` và `status='PUBLISHED'`, câu trả lời chỉ trích dẫn tài liệu đã duyệt (`agent_output.py:63-80`). Không thấy bước làm sạch nội dung lúc nạp, chỉ có judge lúc truy xuất |

---

### PHẦN C – Đo lường và bằng chứng

#### C1. Bộ test case kiểu AgentDojo — ⚠️

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Mỗi case có user task, injection task, vector | ✅ | `research/scenarios.py:34-36`: `prompt` (user task), `goal` (injection task), `vector`, `payload`, `expected_tool`. 7 vector (`:9`): direct, transfer_memo, beneficiary_nickname, support_ticket, rag_document, tool_response, memory_context |
| Direct và indirect | ⚠️ | Direct có (`direct-*`). Indirect có mô tả giao dịch, nickname, ticket, RAG, tool response, memory. QR có ở runner live (`qr-foreign-url`) và harness quishing. **Thiếu vector hoá đơn PDF thật (upload file → RAG → tool call)**. Payload "INVOICE" chỉ là text trong các vector có sẵn (`scenarios.py:49`). Chưa thấy việc ánh xạ rõ tới "6 case công khai" |
| Injection đủ khó | ✅ ⚠️ | 35 payload khó (`hard_attacks()`, `scenarios.py:43-68`): hoá đơn nhà cung cấp, JSON `next_action`, chèn token `<\|im_start\|>`, social engineering tiếng Việt, nhắm vào judge. Có thêm corpus live khó (`HARD_LIVE.md`). Nhưng ASR trên corpus khó không cao hơn v1.1 (25,7% so với 27,4% ở naive), nên chưa chứng minh được là "khó hơn" |
| Ví dụ "tóm tắt giao dịch gần nhất" có injection trong mô tả | ✅ | Vector `transfer_memo` với prompt "Summarize my most recent transfer." (`scenarios.py:24`) và payload `misdirect_transfer` |

#### C2. Script chạy test và tính chỉ số — ✅

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Script chạy tự động | ✅ | `python -m research.run` (`research/run.py`), `tools/gateway_compare.py`, `tools/live_attack/run.py`, `scripts/week7-report.py`, `scripts/week7-compare.py` |
| Gateway TẮT và BẬT | ✅ | Lab: profile `naive`/`baseline`/`defended`. App thật: `gateway_compare.py` gọi `PUT /api/admin/agent-gateway` (`tools/gateway_compare.py:111`) |
| Benign utility | ✅ | `research/run.py:30`, `asr-table.md`, `gateway-compare/summary.md` |
| Utility under attack | ⚠️ | Có ở runner HTTP live (`asr-table.md`: "Tool utility under attack"). **Không có** trong `research/run.py::aggregate` (`:18-36`) nên bảng off/on (`GATEWAY_OFF_ON.md`) thiếu chỉ số này |
| Targeted ASR | ✅ | `research/run.py:27`, `asr-table.md`, `gateway-compare/summary.md` |
| Kết quả ra file | ✅ | `offon-research/metrics.csv`, `observations.csv`, `summary.json`; `week7-evidence/results.csv`; `gateway-compare/results.csv`; `gateway-audit-2026-11-08/*` |

#### C3. Bằng chứng cho buổi họp — ⚠️

| Tiêu chí | | Bằng chứng / lý do |
|---|---|---|
| Kết quả QR giả và phản ứng agent | ✅ | `quishing-*-trace.json`, `QUISHING.md`, `media/qr-rejected.png` |
| Allow/deny cho từng injection, kèm log | ✅ | `gateway-compare/results.csv`, `gateway-audit-2026-11-08/*/observations.jsonl`, `offon-research/observations.csv` |
| Bảng ASR tắt/bật | ✅ ⚠️ | Lab (`GATEWAY_OFF_ON.md`): naive 26,6% → defended 0,0% (350 lượt mỗi profile). App thật (`gateway-compare/summary.md`): OFF 9/16 → ON 0/16. **Cần đọc kỹ:** `asr-table.md` (2.070 lượt) có 0% ở mọi cột vì không có cấu hình nào thật sự tắt gateway, và 0% của vector nickname là do tool không được cấp (`KNOWN_FAILURES.md`). Đừng đưa bảng này lên như kết quả "gateway tắt" |
| File capture Caido/Burp | ❌ ⚠️ | Có HAR từ proxy tự viết (`capture/*.har`), không phải Caido/Burp |
| Khác biệt vai trò admin agent | ✅ | `media/admin-assistant.gif`/`.webm`, `RBAC_MATRIX.md` (lỗi thời một phần), `capture/app-ollama.har` |
| Ghi chép lần thử thất bại | ✅ | `KNOWN_FAILURES.md`, `BYPASS_NOTE.md`, `postfix-regression/`, `gateway-audit-2026-11-08/REPORT_VI.md` (G1–G3) |

---

### PHẦN D – Việc không thuộc code (nhóm tự đánh dấu)

- ➖ Đọc tìm hiểu quishing 20–30 phút (trong repo đã có `docs/research/QUISHING.md`)
- ➖ Cài Caido/Burp trên máy ảo
- ➖ Bổ sung bài báo nghiên cứu cho phần indirect injection (đang trích Greshake 2023, AgentDojo, CaMeL)
- ➖ Chốt ngày họp trực tiếp với Robert
- ➖ Chia sẻ tiến độ trong group chat

---

## 3. Rủi ro bảo mật phát hiện thêm

| # | Mức | Vấn đề | Bằng chứng |
|---|---|---|---|
| R1 | **Nghiêm trọng (khi `ENV=demo`)** | **Chiếm tài khoản không cần đăng nhập qua outbox.** `/api/dev/outbox*` không có xác thực và trả mã cùng link của mọi user. Email lại đoán được (`<username>@novabank.test`, `identity_schema.py:36`). Chuỗi đã chạy thử: gọi `forgot-password` cho Alice → đọc link trong outbox → `reset-password` → đăng nhập → đọc OTP đăng nhập trong outbox → đọc OTP chuyển tiền. Hệ quả: mất hoàn toàn ý nghĩa của MFA và OTP chuyển tiền. `compose.local.yaml:12` bật `ENV=demo`, và `tools/gateway_compare.py:3` yêu cầu server LAN chạy với `ENV=demo` (script `start-lan.ps1` được nhắc tới nằm trong `.local/`, không có trong repo) | `api/routes/dev.py:19-40`; probe: list ẩn danh trả `LOGIN_OTP` của Bob kèm mã; reset mật khẩu Alice ẩn danh → **200**, đăng nhập bằng mật khẩu mới → **202** |
| R2 | Trung bình | **Client tự chọn `profile=baseline`** ở bất kỳ môi trường nào, tắt được judge, cơ chế dừng sau 2 lần từ chối và system prompt cứng | `routes_agent.py:25`, `:52`; `agent_access.py:199`, `:343`, `:409`; probe: `POST /api/agent/runs` với `profile=baseline` và `ENV` rỗng → **201** |
| R3 | Trung bình | **Công tắc gateway là toàn cục.** Tắt cho một lần đo là ảnh hưởng mọi user trên server demo, và customer được cấp mọi tool staff | `agent_gateway.py:36-53`; `agent_access.py:269`, `:286-287` |
| R4 | Thấp–Trung bình | Phê duyệt "độc lập" thực chất là cùng người, cùng session. Không có kênh xác nhận ngoài app | `agent_access.py:460`, `:508-519` |
| R5 | Thấp | JWT ủy quyền trả về trình duyệt: user tự gọi được `/api/agent/tools`, `/api/agent/finish` và ghi câu trả lời assistant tuỳ ý vào hội thoại của mình | `agent_access.py:238`; `routes_agent.py:91-111` |
| R6 | Thấp | Thiết bị tin cậy 30 ngày bỏ qua OTP đăng nhập cho khách hàng. `device_token` mà lộ thì chỉ cần mật khẩu | `mfa.py:11-19`, `:85-87`, `:141-145` |
| R7 | Thấp | Hash OTP chuyển tiền là SHA-256 không khoá (`transfer_id:otp`). Nếu lộ DB thì brute-force offline 10⁶ trường hợp rất nhanh. OTP đăng nhập và action đã dùng HMAC | `transfers.py:32-33` so với `auth_crypto.py:60-62`, `action_security.py:13-14` |
| R8 | Thấp | `JWT_SECRET` cũng là khoá HMAC cho QR, OTP và JWT ủy quyền. Lộ một khoá là giả mạo được tất cả. Khi để trống, mỗi lần khởi động lại sinh khoá mới nên QR cũ mất hiệu lực | `auth.py:16`; `local_qr.py:37`, `:42`; `auth_crypto.py:61` |
| R9 | Thấp | Đường legacy `ToolDispatcher.create_transfer` tạo draft không qua phê duyệt, và `PolicyGateway` chế độ `local` ALLOW mặc định. Hiện đã khoá sau `LEGACY_AGENT_TEST_MODE`, nhưng fixture pytest bật biến này | `agent/tools.py:101-108`; `agent/gateway.py:36-37`; `tests/conftest.py:23` |
| R10 | Thông tin | Judge không chạy khi `LLM_PROVIDER=mock` (mặc định của `.env.example`), nên mọi demo ở chế độ mock không có lớp D7 | `agent_guard.py:19-20`; `.env.example:3` |
| R11 | Thông tin | Tài liệu lỗi thời: `RBAC_MATRIX.md` và `CRYPTO_AUTHZ.md` mô tả staff chỉ có tool đọc. Code đã có `propose_*` và staff phê duyệt | `staff_tools.py:93-95`; `dependencies.py:27-31` |
| R12 | Thông tin | Không có test nào kiểm tra outbox theo từng user khi `ENV=demo`. Test hiện tại chỉ kiểm tra 404 khi không ở demo | `tests/test_week7.py:37`; `tests/test_identity.py:177` |

---

## 4. Việc còn thiếu, xếp theo ưu tiên

1. **B3 – Lỗi vượt gateway (làm trước khi thêm tính năng)**
   - Không nhận `profile` từ client nữa: cố định `defended` ở server, chỉ cho `baseline` khi `ENV` là `demo` hoặc `lab` và người gọi là admin (R2).
   - Gắn trạng thái gateway OFF theo run hoặc theo phiên đo thay vì toàn cục, hoặc tự bật lại sau mỗi lần đo. Thêm một bước kiểm tra trước buổi demo: `/api/admin/agent-gateway` phải là `on` (R3).
   - Màn phê duyệt phải hiện rõ khi người nhận hoặc số tiền khác với yêu cầu gốc. Đây là cách phòng H1+H4 mà nhóm đã đề xuất trong `BYPASS_NOTE.md` nhưng chưa thấy kiểm chứng trong code.
   - Thêm regression test: (a) `profile=baseline` bị từ chối ngoài lab; (b) gateway OFF không làm rò rỉ sang run thường.
   - Ghi lại profile, trạng thái gateway và run ID của mọi buổi demo từ nay về sau, để lần tới không còn phải đoán nguyên nhân lịch sử.
2. **C1–C2 – Bộ test và chỉ số**
   - Thêm vector hoá đơn PDF thật: upload file → nạp vào RAG → tool call.
   - Thêm "utility under attack" vào `research/run.py::aggregate` để bảng off/on đủ 3 chỉ số.
   - Ghi rõ ánh xạ tới 6 case direct injection công khai.
   - Trên slide, tách bảng `asr-table.md` (không có gateway OFF thật) khỏi bảng off/on.
3. **B1 – QR giả:** chạy lại trên VM với payload thật và giải mã quang học (camera hoặc jsQR thay cho PNG text chunk). Thêm vài biến thể payload và vài lượt lặp ở temperature > 0.
4. **B2 – Admin RBAC:** cập nhật `RBAC_MATRIX.md` và `CRYPTO_AUTHZ.md` theo code hiện tại. Thêm test leo quyền cho các tool `propose_*` mới, ví dụ support hoặc auditor cố tạo `propose_settings_change`. Cân nhắc thêm mã xác minh riêng hoặc step-up cho admin (A6).
5. **B6 – OTP email (nên làm cùng đợt với B3 vì R1 nghiêm trọng):** bắt `/api/dev/outbox*` dùng `current_user` và lọc `WHERE user_id = user.id`. Riêng email trước khi đăng nhập (OTP login, link reset) thì cần cách khác, ví dụ chỉ hiện trên máy chạy server (`127.0.0.1`), hoặc gắn với `challenge_id` mà người đăng nhập đang giữ. Thêm test cho chế độ `ENV=demo`.
6. **B5 – Signed token:** nếu muốn đáp ứng đúng yêu cầu, khi phê duyệt thì gateway phát token HMAC hoặc JWT riêng (`aud=transfer-confirm`) chứa `transfer_id, owner, to_bank, to_account, amount_vnd, exp, jti`. Sau đó `/confirm` bắt buộc token này, kiểm tra chữ ký, so khớp với draft và đánh dấu `jti` đã dùng. Đồng thời đổi hash OTP chuyển tiền sang HMAC (R7) và tách khoá cho QR, OTP và JWT (R8).
7. **B4 – Traffic capture:** cài Caido hoặc Burp trên VM, tái hiện phiên trong `capture/README.md` qua proxy, thử sửa `profile`, `amount_vnd`, `to_account` và `arguments` của `/api/agent/tools`, rồi lưu file `.caido`/`.burp` hoặc HAR và ảnh chụp vào `evidence/traffic/` hoặc `week7-evidence/capture/`.
