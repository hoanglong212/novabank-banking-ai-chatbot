# Build Scope 25 chức năng — cập nhật 01/11/2026

Theo PDF 23 trang mới nhất. Phần local đã triển khai và kiểm tra; xem [trạng thái phát hành còn mở](release/STATUS.md). UI tiếng Anh và stack hiện tại được giữ theo quyết định dự án. Không coi bảng này là hoàn tất mọi dòng trong PDF.

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

## Kịch bản Alice–Bob 9 bước

Playwright dùng DB mới, Alice 10 triệu/Bob 8,75 triệu. Backend/OTP/ledger/receipt/notifications thật trong mô phỏng; không reset DB gốc.

| Bước | Điều kiện nghiệm thu | Kiểm chứng |
| --- | --- | --- |
| 1 | Alice đăng nhập, thấy 10 triệu | Browser login và số dư |
| 2 | Alice chuyển Bob 2 triệu | Điền form → review → OTP → confirm |
| 3 | Backend kiểm tra quyền, balance, hạn mức và xác nhận | Draft chưa trừ tiền; test backend cho owner/state/TTL/limits/OTP |
| 4 | Alice còn 8 triệu, Bob tăng 2 triệu | UI/API; CLI đối soát DB E2E cân bằng, ledger tổng 0 |
| 5 | Cả hai có history/reference/receipt | Alice tìm và mở chi tiết/tải PDF; Bob history API và chi tiết từ alert/PDF; snapshots 8 triệu/10,75 triệu |
| 6 | Bob nhận thông báo | Browser Alerts, số tiền, đọc thông báo và giữ trạng thái sau reload |
| 7 | Admin xem giao dịch và audit | Browser Operations tìm reference → xem `TRANSFER_COMPLETED` và balance |
| 8 | Lỗi/gửi lặp không trừ sai | Browser HTTP replay cùng key, insufficient funds; backend fault injection/concurrency/rollback |
| 9 | Người thứ ba không đọc giao dịch Alice/Bob | Charlie login riêng, detail/PDF 404, admin 403, history rỗng |

Bộ E2E hiện có 12 tests; service/LLM thật được kiểm tra riêng. Xem [test plan](release/TEST_PLAN.md) và [evidence](release/STATUS.md).
