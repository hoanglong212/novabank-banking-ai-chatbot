# Hướng dẫn khách hàng demo

Chạy theo [Deployment](DEPLOYMENT.md), mở `http://127.0.0.1:8080`. Alice/Bob/Charlie có username tương ứng, mật khẩu `Alice@2026`, `Bob@2026`, `Charlie@2026`. Sau password phải nhập email MFA. Đây là credential công khai của môi trường mô phỏng.

## Lấy thư mô phỏng

Chạy `backend/.venv/Scripts/python.exe scripts/dev-outbox.py --help` để xem CLI đọc local inbox. Dùng cùng `--db` với server, lọc recipient/kind, rồi đọc đúng thư bằng `--id`. Không gửi OTP vào chat AI. Đăng ký, email verify và reset cũng dùng outbox. TOTP setup nằm trong Profile → Security Center.

## Thao tác chính

| Nhu cầu | Thao tác |
|---|---|
| Xem số dư | Home → Show balance. Số dư ẩn mặc định |
| Chuyển nội bộ | Home → Transfer → NovaBank account ID → amount/content → Continue → kiểm tra tên/phí → OTP → Confirm |
| Liên ngân hàng | Chọn Demo Bank A/B, nhập account giả. PENDING sẽ đổi sau worker. Account tận cùng 0000 tạo tình huống hoàn tiền |
| Biên lai/lịch sử | Activity → filters/search → giao dịch → Download PDF receipt. Biên lai chỉ cho completed |
| Danh bạ/tên tài khoản | Explore → Accounts & recipients. Xác minh và lưu người nhận; nickname không thay identity |
| Thẻ | Explore → Cards → khóa/mở hoặc mua giả lập/trả nợ → review → code. Credit/debit có lịch sử riêng |
| Hóa đơn | Explore → Pay bills → Review payment → code; lưu hóa đơn để nhận nhắc hạn |
| Tiết kiệm | Explore → Savings → nguồn/kỳ hạn/gốc → review → code. Review withdrawal hiển thị lãi dự kiến trước khi chốt |
| Goal/calculator | Explore → Goals & calculator. Loan calculator chỉ tính lịch trả, không mở khoản vay |
| Thống kê | Explore → Spending & budgets → chọn tháng và đặt ngân sách. Đổi category trong Transaction details |
| Sao kê | Explore → Statements → from/to ≤1 năm → PDF/CSV |
| QR | Explore → Demo QR → tạo cho tài khoản của mình. Scan original NovaBank PNG hoặc dán payload, kiểm tra rồi review transfer |
| Hỗ trợ | Explore → Help & support → tạo ticket → reply/attachment; đọc Help library |
| Bảo mật | Profile → đổi contact/password qua current password và OTP; Security Center xem/revoke phiên, login history, TOTP |
| Cài thông báo | Profile → Notification preferences → bật/tắt saved bill reminders/budget alerts → Save. Security và money alerts luôn bật |

## Assistant

Ví dụ: `What is my account balance?`, `What interest rate does NovaBank offer for 6 month savings?`, `Transfer 200000 VND to ACC-BOB-001 content lunch`.

Chọn Defended để dùng source screening và anomaly stop. Nhấn “Assistant runs and sources” → View trace để xem tool và nguồn. Đề xuất thay đổi có Review and approve/Decline; duyệt payment vẫn cần OTP ngân hàng. AI không được phép thực hiện confirm hoặc đọc tài khoản người khác. Nếu inference không đáp ứng, UI hiển thị lỗi và có thể tiếp tục dùng Explore.

QR này không dùng được ở ngân hàng thật. Email/SMS/KYC đều giả lập. Chỉ original PNG export chứa metadata dùng được với decoder; ảnh chụp/cắt QR chưa hỗ trợ. Không nhập dữ liệu tài chính thật vào demo.
