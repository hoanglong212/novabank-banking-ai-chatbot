# Đăng ký, xác minh và khôi phục mật khẩu — M1

Phạm vi người dùng chọn ngày 01/11/2026. Giữ React/Vite/FastAPI/SQLite; không cần thêm thư viện hoặc dịch vụ. Email mô phỏng được lưu trong SQLite **trên máy này**, không gửi email thật.

## Chạy thử

1. Chạy ứng dụng theo README. Migration v3 tự thêm identity khi backend khởi động; không reset số dư/lịch sử. Dùng **Create an account** trên trang đăng nhập.
2. Điền tên hiển thị, username 3–32 ký tự (chữ Latin, số, `_`, bắt đầu bằng chữ), email giả và mật khẩu 15–128 ký tự. Có thể dùng một cụm từ dài, có dấu/khoảng trắng. Tài khoản chưa xác minh chưa đăng nhập được.
3. Từ thư mục gốc dự án, liệt kê hộp thư của đúng DB ứng dụng đang chạy:

```powershell
.\backend\.venv\Scripts\python.exe scripts/dev-outbox.py --db backend/novabank_demo.sqlite3 --email dana@example.test
```

4. Lấy `id` thư `VERIFY_EMAIL` trong kết quả, rồi mở riêng thư đó:

```powershell
.\backend\.venv\Scripts\python.exe scripts/dev-outbox.py --db backend/novabank_demo.sqlite3 --id ID_THU --origin http://127.0.0.1:8080
```

Thay `ID_THU` bằng ID thật. Nếu dùng Vite, truyền `--origin http://localhost:5173`; nếu launcher dùng cổng khác, truyền đúng cổng. Nếu đã cấu hình `DB_PATH`, truyền đúng file đó; lệnh không tự tìm hay tạo DB.

5. Mở `action_url`, bấm **Verify email**, sau đó đăng nhập bằng mật khẩu và mã `LOGIN_OTP` từ hộp thư local ([hướng dẫn MFA](SESSIONS_MFA_VI.md)). Ứng dụng tạo đúng một tài khoản khách hàng với **0 VND** và ledger mapping. Muốn thử chuyển tiền, đăng nhập Alice trong cửa sổ khác để chuyển vào ID tài khoản mới.
6. **Forgot password?** → nhập email → **Send reset link**. Đọc thư `RESET_PASSWORD` bằng cùng lệnh trên, mở URL rồi đặt mật khẩu mới. Link dùng một lần, hết hạn sau **15 phút**. Các JWT cũ bị từ chối ở yêu cầu API tiếp theo; đăng nhập lại bằng mật khẩu mới.

**Verify your email** cho phép gửi lại link xác minh. Link xác minh có hạn 24 giờ; gửi lại làm link cũ mất hiệu lực. Sau xác minh/đặt lại thành công, không tự đăng nhập. Token được bỏ khỏi thanh địa chỉ sau khi ứng dụng đọc fragment; nếu refresh trước khi gửi form, mở lại URL từ hộp thư.

Các tài khoản seed có email `${username}@novabank.test`, ví dụ `alice@novabank.test`. Reset mật khẩu Alice sẽ giữ mật khẩu mới qua các lần khởi động; nút điền mật khẩu demo `Alice@2026` không còn dùng được cho Alice đó. Đây là hành vi chủ ý, không phải mất dữ liệu.

## Hành vi bảo vệ và giới hạn

- API register/forgot/resend trả cùng thông báo cho dữ liệu hợp lệ dù identity có tồn tại hay không. Đăng ký trùng không thay tên/mật khẩu của tài khoản đang chờ. Không nhận `role`, `balance` hoặc quyền từ client; tài khoản mới luôn là customer.
- Token ngẫu nhiên 256 bit, lưu SHA-256 trong bảng token, ràng buộc đúng mục đích. Token, mở tài khoản/ledger, thay password/version và thông báo được commit/rollback trong một transaction SQLite. Gửi trùng đồng thời chỉ tiêu thụ token một lần.
- `dev_outbox` là ngoại lệ có chủ đích: chứa link có token rõ để mô phỏng email. Người có quyền đọc DB có thể dùng link, kể cả reset staff seed. Chỉ dùng local với dữ liệu giả; **không có HTTP API đọc inbox**. CLI chỉ hiển thị link khi chọn `--id`, ẩn link đã hết hạn/đã dùng; link bị xóa trong DB khi tiêu thụ hoặc thay thế. Chưa có job xóa thư hết hạn.
- Giới hạn request lưu SQLite: 20 lần/IP/endpoint/khung 15 phút; tối đa 5 yêu cầu gửi/email/mục đích/khung một giờ. Đếm cả email không tồn tại. Vượt hạn gửi vẫn trả thông báo chung, không phát thư mới. Dùng IP kết nối, bỏ qua forwarded header; chưa tối ưu cho reverse proxy/NAT hoặc nhiều instance. Fixed window cho phép burst quanh ranh giới khung.
- Hash mới dùng PBKDF2-HMAC-SHA256 600.000 vòng; hash seed 310.000 vòng vẫn tương thích. Không tuyên bố HTTP constant-time hoặc không thể dò username qua thời gian phản hồi. Validation auth không phản chiếu password/token vào lỗi 422.
- Migration v4 đã bổ sung login MFA (email/TOTP), refresh rotation, danh sách/thu hồi phiên, idle timeout, Security Center và login history. Lockout lưu SQLite: 5 lần sai trong 15 phút, khóa 15 phút. Full M1 còn sửa profile và đổi mật khẩu đang đăng nhập kèm OTP. Xem [quy tắc phiên/MFA](SESSIONS_MFA_VI.md).

Các quyết định tham khảo [OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) và [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html); đây là demo nghiên cứu, không phải xác nhận tuân thủ tiêu chuẩn.
