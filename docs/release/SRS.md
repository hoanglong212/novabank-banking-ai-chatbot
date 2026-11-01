# SRS — NovaBank simulation

Version triển khai local: 01/11/2026. Nguồn yêu cầu: PDF 23 trang do người dùng cung cấp. Stack giữ nguyên React 19/Vite/TypeScript, FastAPI và SQLite. Đây là ngân hàng giả lập, không kết nối ngân hàng hoặc dịch vụ thanh toán thật.

## Actors và ranh giới

Customer chỉ quản lý dữ liệu của mình. Support xử lý ticket. Operations đọc giao dịch và audit. Auditor có quyền đọc. Admin quản trị khách hàng, trạng thái tài khoản, phí/hạn mức, knowledge và research. Agent chỉ có token `ai:read` và `ai:prepare`, không dùng JWT đăng nhập để xác nhận tiền.

## 25 use cases và điều kiện nghiệm thu

| UC | Hành vi đã triển khai | Tiêu chí chính |
|---|---|---|
| 01 Authentication/MFA | Đăng ký, email verify, reset, email/TOTP, refresh rotation, revoke | MFA trước phiên; token cũ vô hiệu khi đổi mật khẩu/khóa user |
| 02 Dashboard | Số dư ẩn mặc định, tháng hiện tại, thẻ, tiết kiệm, hóa đơn, history | Tổng theo kỳ, loại pending/failed và tránh đếm lại principal |
| 03 Profile | Đổi tên/email/điện thoại/password, security center | Mật khẩu hiện tại + OTP đúng session; email mới nhận code |
| 04 Account | Nickname, trạng thái, thông tin chủ sở hữu | Không đọc/sửa tài khoản khác; đóng chỉ khi không còn nghĩa vụ |
| 05 Transfer | Nội bộ và liên ngân hàng mô phỏng | Atomic posting, OTP, idempotency, phí khóa trong draft |
| 06 History | Tìm kiếm, ngày, trạng thái, hướng, phân trang, chi tiết | Owner filter ở backend |
| 07 Beneficiary | Xác minh tên nội bộ, thêm/xóa, chọn để chuyển | Nickname là dữ liệu không đáng tin |
| 08 Ledger | Nhật ký kép và cache trong cùng transaction | Tổng journal = 0; số dư cache = ledger; trigger bất biến |
| 09 Notifications | Tiền vào/ra, sản phẩm, bảo mật, ngân sách, nhắc hóa đơn, preferences | Owner preferences, critical alerts luôn bật, đọc/đọc tất cả, polling 15 giây, dedupe |
| 10 Receipt | Biên lai PDF tiếng Việt | Chỉ completed/owner, snapshot có nguồn |
| 11 Cards | Debit/credit, khóa/mở, mua giả lập, trả nợ, lịch sử | OTP, credit limit, thẻ frozen không mua được |
| 12 Bills | Điện/nước/internet/mobile, lưu hóa đơn, nhắc hạn, thanh toán | Revalidate trạng thái dưới write lock, không trả hai lần |
| 13 QR | Nhận/đọc QR nội bộ và review transfer | HMAC kiểm tra sửa nội dung, chỉ original PNG/text |
| 14 Savings | 3/6/12 tháng, mở/rút, goal, calculators | Lãi integer, rút sớm 0 lãi, destination khóa vào tài khoản gốc |
| 15 Analytics | Phân loại, biểu đồ, so tháng trước, budgets | Phí tính vào chi; refund thất bại không thành thu nhập |
| 16 Statements | PDF/CSV tối đa 1 năm/10.000 giao dịch | Chủ sở hữu, CSV chống formula injection, hiển thị fee |
| 17 Support | Ticket, reply, attachment, assignment/status | Chủ sở hữu hoặc staff, kiểm tra loại/dung lượng file |
| 18 Admin | Overview/reconcile/user/account/settings/knowledge | RBAC server, xác nhận UI cho hành động quản trị nhạy cảm |
| 19 Assistant | Service riêng, Ollama, SSE progress, history | 4 vòng/8 tool/120 giây; output qua filter trước UI |
| 20 Tools | DTO chặt, owner, intent binding, quota | Không có confirm tool; token agent không vào API thông thường |
| 21 RAG | Chunk/vector nomic, approved sources, source viewer | Không truy xuất draft/untrusted; index cũ không ghi đè content mới |
| 22 Approval | Card/ticket/bill/transfer proposal | Chủ đề xuất + session duyệt, riêng OTP khi phát sinh tiền/thẻ |
| 23 PI Lab | Sandbox reset, 35 scenario/7 vector, 100 benign | Từ chối DB ngoài thư mục nghiên cứu, raw evidence |
| 24 Trace | Runs/calls/model/profile/latency/tokens/decision | Trace theo owner, loại secret, vault encrypted và expiry |
| 25 Security dashboard | Matrix, ASR/utility/FPR, ablation, export | Hiển thị mẫu/lỗi/giới hạn; số liệu từ lần chạy thật |

## Phi chức năng và khác biệt với đề cương

SQLite dùng `BEGIN IMMEDIATE`, không giả lập PostgreSQL `SELECT FOR UPDATE`. Browser dùng bearer token trong sessionStorage và bộ điều phối refresh, không cookie auth. QR là định dạng riêng, không NAPAS. UI giữ tiếng Anh theo quy ước dự án hiện tại. KYC/email/SMS đều mô phỏng. SSE phát tiến độ và tool state, câu trả lời chỉ xuất sau filter.

Phần P2 như khoản vay thật, thẻ ảo, chuyển định kỳ/hàng loạt, live chat, dark mode không nằm trong bản này. Loan calculator chỉ ước tính, không cấp tín dụng. Bản local chưa phải tag phát hành v1.0 hoặc hệ thống ngân hàng production.

## Liên kết truy vết

[Business rules](BUSINESS_RULES.md), [test plan](TEST_PLAN.md), [threat model](THREAT_MODEL.md), [API](API_SPEC.md), [evidence/status](STATUS.md). Mỗi use case có API và UI tương ứng trong các module `backend/app/routes_*` và `frontend/src/components`.
