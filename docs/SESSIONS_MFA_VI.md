# Đăng nhập MFA và quản lý phiên — 01/11/2026

Tất cả customer và staff cần mật khẩu + mã xác minh. Email là hộp thư mô phỏng local, không gửi thư thật. Giữ stack và DB hiện có; không thêm dịch vụ.

## Đăng nhập bằng mã email

1. Nhập username/password, bấm **Sign in**. Trang chuyển sang **Verify sign-in**; lúc này chưa có phiên đăng nhập.
2. Từ thư mục gốc, liệt kê thư cho đúng user và đúng DB:

```powershell
.\backend\.venv\Scripts\python.exe scripts/dev-outbox.py --db backend/novabank_demo.sqlite3 --email alice@novabank.test
```

3. Chọn ID của thư `LOGIN_OTP` mới nhất:

```powershell
.\backend\.venv\Scripts\python.exe scripts/dev-outbox.py --db backend/novabank_demo.sqlite3 --id ID_THU
```

4. Nhập trường `code` vào **Verification code**, bấm **Verify and sign in**. Không đưa mã vào chat AI.

Nếu đổi `DB_PATH`, truyền đúng file DB ứng dụng đang chạy. Địa chỉ seed là `<username>@novabank.test`; tài khoản đăng ký mới dùng email đã nhập. CLI liệt kê chỉ metadata, phải chọn `--id` mới hiện mã; mã hết hạn/đã dùng không hiện. Không có API HTTP đọc hộp thư.

Mã email có hạn 2 phút; yêu cầu đăng nhập có hạn 5 phút. Gửi lại sau 30 giây, tối đa 3 lần; gửi lại không gia hạn yêu cầu hoặc xóa số lần sai. Tổng 5 lần sai mật khẩu/MFA trong 15 phút sẽ khóa 15 phút; bộ đếm lưu SQLite.

## Authenticator và Security Center

Mở **Profile → Security Center**:

- **Active sessions**: xem phiên hiện tại và phiên khác; **Sign out session → Confirm sign out** thu hồi phiên khác ngay ở backend. Nút Sign out của ứng dụng thu hồi phiên hiện tại.
- **Login history**: xem lịch sử thành công/thất bại và thông tin IP/user-agent theo trang. Thời gian hiển thị theo Việt Nam. IP/user-agent chỉ là thông tin tham khảo, không phải chứng thực thiết bị.
- **Set up authenticator**: nhập mật khẩu hiện tại, thêm tài khoản NovaBank dạng time-based vào ứng dụng xác thực bằng **Setup key**, rồi nhập mã 6 chữ số để bật. Mã cùng bước thời gian không được dùng lại; nếu vừa xác nhận setup, chờ mã tiếp theo khi đăng nhập.
- **Use an email code instead** ở trang MFA là cách dự phòng khi không dùng được authenticator.
- **Disable authenticator** cần mật khẩu và mã email riêng từ thư `DISABLE_TOTP_OTP`. Bật/tắt authenticator thu hồi các phiên khác và yêu cầu đăng nhập đang chờ; email MFA vẫn bắt buộc.

Khóa setup chỉ tồn tại trong bộ nhớ trang và được xóa khi đóng hộp thoại/hết hạn. Không gửi khóa cho AI. TOTP lưu mã hóa Fernet trong DB; `MFA_ENCRYPTION_KEY` có thể cấu hình qua môi trường. Nếu không cấu hình, khóa được tạo cạnh DB ở **`<DB_PATH>.mfa.key`**. Backup DB cần giữ cả file khóa (hoặc khóa môi trường), không commit khóa. Mất khóa thì dùng email dự phòng, tắt rồi thiết lập lại authenticator.

## Thời hạn phiên và khởi động lại

- Access JWT: 5 phút; refresh token xoay vòng một lần, chỉ lưu hash ở backend. Dùng lại refresh token đã tiêu thụ thu hồi phiên đó. Nếu mất phản hồi refresh, cần đăng nhập lại.
- Phiên không hoạt động: 5 phút; giới hạn tuyệt đối: 8 giờ. API đọc, polling Alerts và refresh không kéo dài thời gian idle. Tương tác trình duyệt gửi activity tối đa mỗi 30 giây; backend quyết định thời hạn.
- Thông tin phiên lưu trong `sessionStorage` theo tab. Đóng tab xóa bản lưu trên tab nhưng không lập tức thu hồi bản ghi backend; dùng Sign out hoặc Security Center để thu hồi. Không coi đây là cơ chế HttpOnly/cookie chống XSS.
- Migration v4 khiến JWT cũ không có session ID phải đăng nhập lại. Nếu `JWT_SECRET` không ổn định, restart làm JWT truy cập và mã email đang chờ mất hiệu lực; refresh của phiên chưa hết hạn có thể cấp JWT mới. Đặt secret ổn định nếu cần khởi động lại mà vẫn dùng mã đang chờ.
- Khôi phục mật khẩu thu hồi toàn bộ phiên, refresh và MFA challenge cũ.

## Docker

Image hiện đóng gói CLI đọc inbox. Sau khi khởi động container `novabank-demo`, dùng terminal khác:

```powershell
docker exec novabank-demo python /app/scripts/dev-outbox.py --db /data/novabank_demo.sqlite3 --email alice@novabank.test
docker exec novabank-demo python /app/scripts/dev-outbox.py --db /data/novabank_demo.sqlite3 --id ID_THU
```

Luồng Docker chưa được chạy kiểm chứng trong đợt này. Các E2E local dùng backend thật với DB tạm và mock AI. Sửa profile, đổi mật khẩu khi đang đăng nhập kèm OTP, gửi email thật và job dọn thư hết hạn vẫn là phần tiếp theo.
