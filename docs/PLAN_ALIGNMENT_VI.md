> Historical milestone record. Current full-roadmap implementation and remaining release conditions: [STATUS](release/STATUS.md).

# Đối chiếu kế hoạch Banking Web App + AI Agent

Ngày rà soát ban đầu: 31/10/2026. Cập nhật 01/11/2026 theo các PDF `(1)` và `(2)` cùng 21 trang. Bản `(2)` ghi nhận kịch bản Alice–Bob đã qua; người dùng chọn làm tiếp đăng ký/xác minh/khôi phục mật khẩu thuộc M1. Bảng baseline dưới đây giữ lại hiện trạng trước triển khai; trạng thái mới nằm trong [Build Scope và nghiệm thu](BUILD_SCOPE_VI.md).

## Quyết định đã chốt

- Người dùng chọn **giữ React/Vite/TypeScript/Tailwind + FastAPI + SQLite**, làm tiếp phần thiếu. Không khởi tạo lại repo, chuyển Next.js hay cài PostgreSQL/Redis/Mailpit.
- PDF mới đã cung cấp “Build Scope 25 chức năng” và kịch bản Alice–Bob 9 bước. Hạn nộp thực tế vẫn chưa được xác nhận. Checklist được theo dõi tại [BUILD_SCOPE_VI.md](BUILD_SCOPE_VI.md).
- Giữ NovaBank, giao diện tiếng Anh, dữ liệu và thiết kế đang có. Các thay đổi giao diện chưa commit có trước đợt này được bảo toàn.
- Tái sử dụng AI hiện có, nhưng ưu tiên hoàn thiện banking core trước khi mở rộng nghiên cứu như thứ tự trong PDF.
- PDF là đặc tả tham khảo để triển khai, không phải lệnh tự động tạo repo, push, tag, cài dịch vụ hoặc triển khai VPS.

## Hiện trạng trước triển khai

| Mốc | Đã có, có thể tái sử dụng | Còn thiếu / chưa đạt |
| --- | --- | --- |
| GĐ0 | Thương hiệu, React UI, FastAPI OpenAPI, Dockerfile, launcher, `.env.example`, pytest, component checks | SRS/25 use case, ERD, Business Rules, threat model cập nhật, Compose/CI/lint; stack hạ tầng trong PDF không áp dụng nguyên xi |
| M1 | 2 tài khoản demo, password hash, JWT 60 phút, lockout 5 phút, ownership, profile/tài khoản qua `/api/me` | Đăng ký/verify/reset password, MFA đăng nhập, refresh rotation, thu hồi phiên/idle timeout, RBAC 5 vai trò, login history, quản trị khách hàng |
| M2 | Draft → OTP → xác nhận → biên lai UI, cập nhật số dư nguyên tử, giới hạn/lần/ngày, lịch sử Alice/Bob | Sổ cái kép bất biến, đối soát, idempotency trả kết quả cũ, trạng thái tài khoản, quote expiry; danh bạ, API lọc/phân trang, PDF, notifications/SSE, admin, reversal/liên ngân hàng bất đồng bộ |
| M3 | Dashboard, activity, QR, ticket tạo qua AI, FAQ | Thẻ, hóa đơn, tiết kiệm, ngân sách, sao kê, quản trị/support workflow, phân loại nguồn không tin cậy |
| M4 | Mock/Ollama/LangGraph, dispatcher/schema/ownership, input guard, pseudonymization, AI chỉ tạo draft, lịch sử chat theo user | Agent tách service và token `ai:read`/`ai:prepare`, RAG có nguồn, streaming, `agent_runs`/`agent_tool_calls`, 60–100 functional cases, profiles |
| M5 | Dry-run policy panel, tool events, test negative với model giả | Sandbox reset, ≥30 scenario/7 vector, harness model × profile × repetition, ablation, trace viewer đầy đủ, ASR/utility/false positives; không dùng mock để công bố độ an toàn LLM |
| M6 | README, demo script, bộ kiểm tra local | CI, E2E browser mới, coverage tài chính ≥80%, backup/restore, HTTPS, báo cáo/video/slide |

Bằng chứng baseline: `backend/.venv/Scripts/python.exe -m pytest -q` → **94 passed**; `npm run build` và `npm run test:components` → **9 nhóm kiểm tra pass**. Chưa chạy model thật trong đợt rà soát này.

## Khác biệt phải xử lý có chủ đích

1. PDF dùng 10 triệu cho Alice; demo đang có 12,5 triệu. Không reset DB của người dùng. Test concurrency dùng DB riêng có 10 triệu.
2. SQLite không có `SELECT FOR UPDATE`. Giữ SQLite bằng transaction `BEGIN IMMEDIATE` để tuần tự hóa ghi; không coi đó là kiểm chứng PostgreSQL hay khả năng tải cao.
3. Lịch sử seed không phải sổ cái kế toán. Khi thêm ledger, ghi số dư mở sổ tại thời điểm nâng cấp, có tài khoản đối ứng. Giữ lịch sử cũ như dữ liệu demo, không bịa lại bút toán quá khứ.
4. Mã đang gọi dịch vụ danh sách/ảnh VietQR bên ngoài; PDF yêu cầu QR mô phỏng không kết nối VietQR thật. Cần bước thay QR riêng; không tuyên bố ứng dụng đã hoàn toàn offline.
5. ToolDispatcher dùng DB trong cùng tiến trình backend. Điều này chưa đáp ứng ranh giới Agent Service chỉ gọi Banking API bằng token giới hạn quyền ở M4.
6. PDF nhầm tên M3 tại cổng 03/01/2027; dựa theo bảng lịch và mục 7, đây là cổng **M2 Core Banking**. Chưa chốt lại lịch vì chưa có hạn nộp.

## Thứ tự tiếp tục

1. Foundation và bước 5–7 đã được kiểm chứng local: chi tiết/biên lai PDF, thông báo, RBAC/admin tối thiểu. CI vẫn chờ chạy trên GitHub; không tự push theo chỉ thị trong PDF.
2. Đăng ký/verify/reset, login MFA (email/TOTP), refresh rotation/quản lý phiên/idle timeout, lockout SQLite và lịch sử đăng nhập đã được kiểm tra local. Xem [hướng dẫn MFA](SESSIONS_MFA_VI.md). M1 còn sửa profile, đổi mật khẩu với OTP và quản trị tài khoản; CI/review độc lập còn chờ.
3. Hoàn thiện phần còn lại M2: danh bạ, liên ngân hàng mô phỏng bất đồng bộ/reversal, đối soát định kỳ và QR nội bộ. Kịch bản 9 bước có test tự động riêng, không tương đương hoàn thành toàn bộ M1/M2.
4. Sau cổng core mới mở rộng M3, rồi tách agent/RAG/trace (M4), lab (M5), cuối cùng M6. Mỗi mốc có bằng chứng thực chạy, chưa tag tự động.

## Mô hình nghiên cứu cần thiết kế từ đầu

Các bảng sau là thiết kế cho M4–M5, **chưa phải schema đã triển khai**:

- `agent_runs`: id, user_id, conversation_id, profile, model, prompt_version, started_at, finished_at, status, token_usage, latency_ms.
- `agent_tool_calls`: id, run_id, sequence, tool_name, masked_arguments, decision, reason, result_summary, duration_ms; không OTP/token.
- `security_events`: id, run_id, user_id, layer, event_type, decision, masked_evidence, created_at.
- `attack_scenarios` / `attack_results`: vector, payload/sandbox fixture, expected tool/argument/canary, model/profile/repetition/seed, measured result, trace id.
- `knowledge_documents` và các nguồn ticket/beneficiary/memo: `source_type`, `trust_level`, owner, version. Dữ liệu truy xuất là dữ liệu không tin cậy, không phải chỉ thị.

## Tiến độ đợt triển khai

Đã triển khai và kiểm chứng phần foundation của M2: ledger kép bất biến, opening migration giữ dữ liệu cũ, posting nguyên tử, idempotency, trạng thái tài khoản, draft TTL/OTP atomic, đối soát CLI và UI retry. **136 test backend**, **11 nhóm frontend** và production build pass; live API smoke trên DB riêng và migration bản sao DB hiện có đều đạt. Chưa đánh dấu M1, M2 hay toàn bộ lộ trình hoàn thành. Xem [bằng chứng và giới hạn](banking-core-completion-2026-10-31.md).

Đợt 01/11 bổ sung history queries, snapshot giao dịch, biên lai PDF, thông báo tiền vào/ra, 5 vai trò demo và trang Operations. Bằng chứng mới, các cổng chưa chạy và phần còn thiếu được ghi riêng tại [completion.md](completion.md).
