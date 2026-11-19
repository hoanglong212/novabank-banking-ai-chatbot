# Kiểm tra bổ sung các kiểm soát API

Các kết quả dưới đây dùng cùng commit `0548e998e44c9fb5400ae9211ffdaf6cdf677074`, seed `20261115` và SQLite tạo mới trong thư mục tạm. Các ca do người nghiệm thu viết. [Kết quả máy đọc được](controls-results.json) ghi mức kiểm tra và quan sát DB, không chứa token hoặc OTP.

| ID | Kết quả | Bằng chứng | Giới hạn |
|---|---|---|---|
| API-02 | WEAK | `posting.validate_accounts` trả `ACCOUNT_NOT_OWNED` với fixture không khớp chủ tài khoản, số dư của tài khoản giữ nguyên 39.450.000 VND. Kiểm tra lọc owner ngay tại SQL ở `backend/app/posting.py:18`; tầng chuẩn bị giao dịch còn kiểm tra tài khoản trong principal ở `backend/app/transfers.py:85`. | Xác nhận tầng nghiệp vụ. Chưa chạy tình huống ghi sai chủ qua HTTP. |
| API-03 | WEAK | DTO `Nickname` chấp nhận nickname hợp lệ, từ chối đủ role, balance, owner_id với `extra_forbidden`. Cấu hình ở `backend/app/identity_schemas.py:6` và `backend/app/routes_customer.py:22`. | Kiểm tra validator của một DTO. Chưa chứng minh thao tác cập nhật xuyên HTTP giữ nguyên các trường trong DB của mọi DTO. |
| API-05 | WEAK | POST công khai không có delegation tới route tool trả 401 với body có detail. Số agent_calls trước/sau bằng 0. Dependency delegation ở `backend/app/routes_agent.py:56` và `:85`. | Chỉ bằng chứng từ chối khi thiếu credential. Không chạy bypass. |
| API-08 | WEAK | Hai worker ghi sổ qua transaction riêng trên DB tạm, cùng số tiền 19.100.001. Một journal commit, một transaction nhận INSUFFICIENT_FUNDS. Chỉ hai dòng ledger tổng bằng 0. Số dư cuối 19.099.999 và 58.550.001 VND. `backend/app/posting.py:51`, `backend/app/identity.py:32`. | Kiểm tra tranh chấp tại tầng SQLite + posting. Chưa xác nhận các tầng HTTP, OTP và xác nhận chuyển tiền đồng thời. |
| API-09 | WEAK | Truy vấn bình thường với tên `O'Brien` trả 200 và danh sách rỗng. `backend/app/customer_services.py:97` bind owner và ba giá trị LIKE, escape ký tự wildcard. | Kiểm tra mã và chuỗi tên thông thường ở một endpoint. Không chạy payload SQL injection. |
| API-11 | WEAK | Sau bước mật khẩu: HTTP 202, có challenge và chưa cấp access token, session DB 0→0. `authenticate` từ chối challenge với 401. HTTP /me khi chưa đăng nhập trả 401; sau xác thực MFA trả 200 đúng user, session DB 0→1. `backend/app/auth.py:90`, `backend/app/mfa.py:90`. | Credential trung gian được kiểm tại hàm xác thực. Chưa thực thi ca HTTP gửi credential trung gian tới endpoint yêu cầu session. |
| API-12 | WEAK | OTP đăng nhập bị từ chối khi hết hạn đúng tại biên, dùng lại hoặc sai. Cả ba trả 400 từ hàm nghiệp vụ. Đặt fixture đã có bốn lỗi, một lần nhập sai khiến số lỗi bằng 5, challenge bị tiêu thụ, trạng thái khóa được ghi và Bob có 0 session. `backend/app/mfa.py:26`, `:107`; `backend/app/session_security.py:34`. | Bao phủ logic login email OTP với đồng hồ mô phỏng, không tạo chuỗi thử nhiều mã và không kết luận cho mọi endpoint OTP chuyển tiền. |

Tái chạy bằng Python venv có dependencies backend và một clone sạch đúng SHA:

```powershell
rtk proxy backend\.venv\Scripts\python.exe verify/mentor-controls.py <clean-checkout> docs/release/week8/verify-evidence/controls-results.json
```

Lượt chạy đầu đã xuất đủ kết quả rồi gặp lỗi Windows khi dọn SQLite tạm đang mở. Verifier được điều chỉnh để giải phóng kết nối trước khi xóa thư mục tạm. Lượt chạy thứ hai tạo lại DB từ đầu, kết thúc mã 0 và trả cùng kết quả WEAK cho cả bảy ID.
