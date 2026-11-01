# Bản local đang chạy

Khởi chạy ngày 01/11/2026 theo yêu cầu người dùng.

- Ứng dụng: http://127.0.0.1:8080
- Agent riêng: cổng 8093; Qwen `qwen2.5:7b` qua Ollama đang có trên máy.
- Database riêng: `.local/local-deploy/novabank.sqlite3`. Có 5 khách hàng và 6 tháng dữ liệu giả; không thay dữ liệu gốc.
- Knowledge: 8 tài liệu/chunk đã index bằng `nomic-embed-text:latest`.

## Đăng nhập

Khách hàng: `alice` / `Alice@2026`. Quản trị: `admin` / `Admin@2026`.

Sau khi nhập tài khoản và mật khẩu, lấy mã email MFA mô phỏng bằng lệnh dưới tại thư mục dự án:

```powershell
.\backend\.venv\Scripts\python.exe .local/local-deploy/show-code.py alice
```

Đổi `alice` thành `admin` nếu đăng nhập quản trị. Mã chỉ nhập vào màn hình xác minh đăng nhập của ngân hàng. Nếu không còn mã hợp lệ, bấm gửi lại mã trên màn hình đó rồi chạy lại lệnh.

## Khởi động lại khi cần

Các tiến trình hiện được giữ bởi phiên làm việc; không cài Windows service hoặc tự khởi động cùng máy. Sau khi tiến trình cũ đã dừng, chạy tại thư mục dự án:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .local/local-deploy/start.ps1
```

Launcher dùng lại đúng database này và bản frontend đã build. Ctrl+C tại terminal launcher dừng cả bank và agent. Không chạy launcher thứ hai trong khi cổng 8080/8093 còn đang dùng.

## Kiểm tra sau khởi chạy

Build TypeScript/Vite đạt; frontend và assets trả HTTP 200; `/api/ready` báo ready; agent health đạt; đăng nhập qua MFA, dashboard và logout trên Chromium đạt, không có page error. Qwen gọi `get_account_balance` qua service riêng thành công và số dư không đổi. Kết quả nằm trong `.local/local-deploy/verification.json` và `browser-check.json`.

Lệnh khởi chạy nền ban đầu bị duyệt tự động từ chối với thông báo `blocked by policy`; đã khởi chạy thành công bằng launcher có sẵn trong tiến trình được phiên làm việc quản lý. Không cài thêm dependency hoặc dịch vụ.
