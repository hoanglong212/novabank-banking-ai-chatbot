# Thiết kế database dùng chung cho NovaBank

Nhóm dùng một bản NovaBank trên máy chủ qua HTTPS. Bản web trên máy chủ và frontend chạy từ repo đều gọi cùng Bank API. Bank đọc và ghi một SQLite trên đĩa của máy chủ. Người mở URL chỉ cần trình duyệt và tài khoản NovaBank của mình.

```text
Trình duyệt hoặc frontend Vite
              |
            HTTPS
              |
         Caddy → Bank API → SQLite trong volume dùng chung
                    |
                    └── Agent và Ollama qua mạng Docker
```

## Dữ liệu và quyền truy cập

| Nghiệp vụ | Bảng hiện tại | Ai có quyền |
| --- | --- | --- |
| Đăng nhập, phiên và MFA | `users`, `user_sessions`, `mfa_settings` | Bank xác thực từng phiên và áp dụng quyền theo role. |
| Số dư, chuyển tiền và đối soát | `accounts`, `transfers`, `transactions`, `ledger_entries` | Customer thao tác trên tài khoản của mình. Bank ghi ledger theo giao dịch nguyên tử và kiểm tra idempotency khi xác nhận. |
| Chat và đề xuất của Agent | `conversations`, `messages`, `agent_runs`, `tool_approvals` | Hội thoại theo chủ sở hữu. Agent dùng token giới hạn qua API của Bank. |
| Cấu hình và tri thức ngân hàng | `bank_settings`, `knowledge_documents`, `knowledge_chunks` | Thay đổi qua quyền quản trị hiện có. |

Một người đăng nhập cùng tài khoản từ hai máy sẽ thấy cùng lịch sử sau khi tải lại. Hai tài khoản khác nhau vẫn có dữ liệu riêng. Giao dịch hợp lệ giữa hai tài khoản thay đổi ledger chung, nên sau khi xác nhận, hai phía đọc được số dư và lịch sử đã cập nhật qua API. SQLite và các khóa ký nằm trên máy chủ. Người dùng và Agent dùng API chứ không nhận quyền mở file DB.

## Đưa DB chung vào sử dụng

1. Chọn một máy chủ Linux, tên miền và mạng nhóm được phép. Làm theo [hướng dẫn HTTPS](DEPLOYMENT.md#chia-sẻ-qua-https) để chuẩn bị `.env.hosted`, key và volume.
2. Với môi trường mới, dùng seed dữ liệu giả sẵn có. Nếu đã có bản hosted, giữ volume đang gắn vào `/data`. Mặc định là `novabank-demo_bank-data`. Nếu cần lấy dữ liệu từ một máy cũ, chọn một snapshot làm nguồn và phục hồi cả DB lẫn key MFA theo [quy trình backup](DEPLOYMENT.md#backup-và-restore) trước khi chuyển người dùng. Các bản SQLite riêng hiện tại có thể chứa cùng ID seed với lịch sử khác nhau, nên việc gộp chúng cần đối soát theo nghiệp vụ.
3. Mở URL HTTPS để dùng chung. Thành viên đang sửa frontend đặt `NOVABANK_DEV_API_TARGET` trong `frontend/.env.shared.local` rồi chạy [`npm run dev:shared`](../../frontend/README.md#use-the-shared-database). Lệnh yêu cầu URL HTTPS của nhóm ngay khi khởi động. Thay đổi schema hoặc backend chỉ có hiệu lực trên DB chung sau khi người vận hành cập nhật Bank trên máy chủ.
4. Dùng một tài khoản thử riêng cho mỗi người. `alice`, `bob` và `charlie` có sẵn cho demo nhanh. Với nhiều người hơn, đăng ký bằng địa chỉ thử nghiệm riêng. NovaBank mô phỏng email, nên người vận hành lấy link xác minh bằng `dev-outbox.py` trên máy chủ và chuyển riêng cho đúng chủ tài khoản:

   ```sh
   docker compose --env-file .env.hosted exec bank python /app/scripts/dev-outbox.py \
     --db /data/novabank_demo.sqlite3 --email teammate@novabank.test
   docker compose --env-file .env.hosted exec bank python /app/scripts/dev-outbox.py \
     --db /data/novabank_demo.sqlite3 --id MESSAGE_ID
   ```

   Thay phần origin loopback trong `action_url` bằng URL HTTPS của nhóm và giữ nguyên fragment xác minh. Sau khi xác minh, tài khoản mới có số dư ban đầu bằng 0. Mã MFA khi đăng nhập lấy từ demo inbox trong giao diện.

## Vận hành và kiểm tra

- Chạy một instance Bank trên cùng máy với volume. Compose tham chiếu volume đã được tạo trước để một lần cập nhật app tiếp tục dùng đúng file. Volume chứa DB cũng giữ key MFA đi kèm file. Backup mount volume chỉ đọc và tạo snapshot mã hóa. Giữ bản sao dự phòng ngoài máy chủ và giữ key giải mã riêng.
- Trước khi cập nhật schema, tạo snapshot và thử restore vào đường dẫn mới. Sau cập nhật, kiểm tra `/api/ready`, đăng nhập và đối soát ledger trước khi mở lại cho nhóm.
- Kiểm tra bằng hai phiên độc lập. Tạo cuộc trò chuyện ở phiên Alice thứ nhất và tải lại ở phiên Alice thứ hai để thấy cùng dữ liệu. Bob không được thấy hội thoại của Alice. Sau khi khởi động lại Bank với cùng volume, Alice vẫn đọc được cuộc trò chuyện đó.
- Các stack trên laptop vẫn là môi trường thử độc lập. Dùng [Docker quick start](../../README.md#quick-start-with-docker) cho thử nghiệm có thể reset và URL HTTPS cho dữ liệu nhóm.

SQLite phù hợp với demo một máy và tải ghi nhỏ. Giữ DB trên volume local của máy chạy Bank. Nếu cần nhiều instance Bank ghi đồng thời trên nhiều máy, lập kế hoạch chuyển sang PostgreSQL và kiểm thử lại migration, ledger, khóa giao dịch và backup. Xem [hướng dẫn chọn SQLite](https://sqlite.org/whentouse.html).
