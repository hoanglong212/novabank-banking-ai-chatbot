# Hướng dẫn vận hành demo

Các tài khoản staff `support`, `operations`, `auditor`, `admin` dùng password viết hoa chữ đầu + `@2026`, đều qua MFA. Không dùng credential demo trên internet nếu không có lớp hạn chế truy cập như cấu hình Caddy đi kèm.

| Vai trò | Quyền thực tế |
|---|---|
| Support | Ticket/reply/assign/status/attachments; không sửa phí hoặc đọc tài chính toàn hệ thống |
| Operations | Overview, transaction/audit reads; không sửa user/account/settings, không xem danh sách ticket hay research |
| Auditor | Đọc transaction/audit; không đọc nội dung ticket khách, không truy cập research hay ghi settings |
| Admin | Các quyền đọc, support và settings:write; quản lý customer identities, account state, knowledge, research |

Operations → Overview hiển thị reconciliation gần nhất. “Run reconciliation” không sửa số dư; nếu mismatch phải điều tra journal/cache. Không sửa tay completed history. Worker tự đối soát mỗi ngày, xử lý external pending, nhắc hóa đơn lưu và xóa secret outbox/vault hết hạn.

Customers: disable sign-in thu hồi toàn bộ phiên, tăng auth_version. KYC chỉ có ý nghĩa mô phỏng, không xác thực giấy tờ thật. Freeze ngăn chi tiền; API close chỉ chấp nhận zero balance và không còn nghĩa vụ. UI xác nhận trước thay đổi trạng thái. Settings thay phí áp dụng draft mới, hạn mức kiểm tra lại ở confirm. Tắt assistant chặn tạo run và các boundary agent hiện hữu.

Knowledge: thêm/sửa văn bản, provenance, trạng thái và trust. Chỉ PUBLISHED + approved cho customer search. Sau thay đổi, Rebuild search index dùng `nomic-embed-text:latest` local. Chưa có model thì thao tác trả lỗi rõ ràng, không tự tải model. Source không được dùng làm chỉ dẫn cho agent.

Research chỉ được truy cập bằng admin khi cấu hình `RESEARCH_SANDBOX_ENABLED=true` (mặc định false), kể cả đọc/download. Một full run gồm Qwen và Llama, 3 profile; naive luôn ở sandbox riêng. Không copy DB ngân hàng vào lab. Đợt sửa nghiệm thu hiện tại không chạy lại AI-14/PI-05/PI-06.

Support được đọc alerts riêng của tài khoản support; thông báo tiền của khách không xuất hiện. Audit thay đổi account/customer/settings lưu before/after trong `reason_code` dạng JSON. Hạn mức vẫn được kiểm tra lúc confirm, phí khóa khi tạo draft.

Backup: giữ key riêng archive. Restore vào đường dẫn mới rồi kiểm tra integrity/ledger trước chuyển server sang DB đó. Khi đổi DB phải đi kèm `.mfa.key` tương ứng. Nếu dùng MFA_ENCRYPTION_KEY qua environment, lưu key đó riêng vì nó không nằm trong file backup. Giữ JWT_SECRET ổn định để QR và OTP/HMAC còn hợp lệ qua restart. [Deployment](DEPLOYMENT.md) có lệnh cụ thể.

Logs chỉ request ID/method/status/duration. Không ghi OTP/access/refresh token. Không gửi thư hay tin nhắn thật từ các workflow mô phỏng.
