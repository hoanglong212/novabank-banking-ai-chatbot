# Chạy Agent, chia sẻ bản demo và khôi phục dữ liệu

## Agent từ bản clone mới

Từ thư mục repo, chạy `docker compose -f compose.local.yaml up -d --build` rồi mở <http://127.0.0.1:8080>. Docker Compose khởi động Bank, Agent và Ollama. Job `models` tải các model còn thiếu rồi thoát với mã 0. Đợi [Agent readiness](http://127.0.0.1:8080/api/ready) báo `ready` trước khi dùng Assistant.

Đăng nhập `alice / Alice@2026`, lấy mã xác thực bằng link demo inbox trên màn hình, rồi vào Assistant hỏi **What is my account balance?**. Máy chạy Docker cần internet ở lần build và tải weights đầu. Bộ mặc định gồm Qwen 7B, Llama 3B và Nomic embeddings. Dành khoảng 7 GB cho weights ngoài dung lượng image và nên có 16 GB RAM cho host. Thời gian phản hồi phụ thuộc CPU/GPU.

| Khi gặp | Cách kiểm tra |
| --- | --- |
| Lần đầu chạy lâu hoặc app chưa mở được | Xem `docker compose -f compose.local.yaml ps -a` và `docker compose -f compose.local.yaml logs models ollama agent bank`. `models` ở trạng thái `Exited (0)` là bình thường. |
| Port 8080 đang được dùng | Tạo `.env` ở root từ [.env.example](../../.env.example) nếu chưa có. Đặt `NOVABANK_PORT=8081`, chạy lại `up -d --build` và mở <http://127.0.0.1:8081>. |
| Assistant báo chưa sẵn sàng | Kiểm tra `/api/ready` trên cổng hiện tại và log Ollama. Sau khi sửa lỗi hoặc đổi model, chạy lại `up -d --build`. |
| Muốn chạy demo nhẹ không tạo phản hồi bằng model | Đặt `LLM_PROVIDER=mock` trong `.env` ở root. Assistant sẽ ghi nhãn phản hồi demo và bỏ qua tải weights. |

`docker compose -f compose.local.yaml down` giữ các volume SQLite và Ollama. Sau khi pull bản mới, chạy lại lệnh `up -d --build`.

## Chạy native trên Windows

Làm theo [các lệnh cho Windows](../../README.md#native-windows-development). Lần đầu, `-Setup` cài dependencies và tạo `backend/.env` từ [mẫu native](../../backend/.env.example) nếu file chưa tồn tại. Với file cũ, đặt `ENV=demo` để hiện hộp thư mô phỏng. `-Mode ollama` ghi đè chế độ trong file cho lần chạy đó.

Với DB phong phú mới, không thay DB cũ:

```powershell
.\backend\.venv\Scripts\python.exe scripts/seed-demo.py --out .local/my-demo.sqlite3
.\backend\.venv\Scripts\python.exe scripts/serve.py --db .local/my-demo.sqlite3
```

Seed từ chối target đã tồn tại. Tạo 5 customer, 6 tháng dữ liệu giả, 10 thẻ, 20 hóa đơn và 5 savings. Bảy history legacy từ seed gốc vẫn được phân biệt với ledger snapshots mới.

## Chia sẻ qua HTTPS

Trên máy chủ Linux của nhóm, cần Docker Engine với lệnh `docker compose`, tên miền và IPv4 có thể truy cập. Trỏ bản ghi DNS A về máy chủ và mở cổng TCP 80/443 cho Caddy. Compose cũng mở UDP 443 cho HTTP/3. Caddy dùng địa chỉ kết nối trực tiếp để giới hạn reviewer. Nếu đặt sau proxy khác, áp dụng giới hạn truy cập ở proxy nhận kết nối từ trình duyệt.

Từ thư mục repo, sao chép [.env.hosted.example](../../.env.hosted.example) và điền file riêng trên máy chủ:

```sh
umask 077
cp -n .env.hosted.example .env.hosted
```

| Biến bắt buộc | Giá trị cần điền |
| --- | --- |
| `DEMO_DOMAIN` | Tên miền đã trỏ DNS, ví dụ `review.example.com`. Điền tên miền, bỏ phần giao thức và đường dẫn. |
| `ACME_EMAIL` | Email vận hành nhận thông báo chứng chỉ. |
| `DEMO_ALLOWED_NETWORKS` | IPv4 hoặc CIDR thực của reviewer hay VPN, cách nhau bằng dấu cách, đặt trong dấu ngoặc kép. |
| `JWT_SECRET` | Giá trị riêng tạo bằng `openssl rand -hex 32`. Giữ nguyên giữa các lần khởi động. |
| `BACKUP_KEY_FILE` | Đường dẫn tuyệt đối tới file key Fernet riêng trên máy chủ. |

Ví dụ tạo key Fernet trên máy chủ dùng Docker rootful. Lệnh tạo file mới và báo lỗi nếu đường dẫn đã có key:

```sh
umask 077
mkdir -p .local/secrets
(set -C; openssl rand -base64 32 | tr '+/' '-_' > .local/secrets/backup.key) &&
  sudo chown 10001:10001 .local/secrets/backup.key &&
  sudo chmod 0400 .local/secrets/backup.key
```

Điền đường dẫn tuyệt đối của file này vào `BACKUP_KEY_FILE`. Cách đặt quyền trên cấp quyền đọc cho UID 10001 của container backup. Giữ `.env.hosted` và key ngoài Git.

Lần đầu tạo một DB dùng chung mới, chuẩn bị volume trên máy chủ:

```sh
docker volume create novabank-demo_bank-data
```

Nếu đã chạy hosted, dùng lại volume đang giữ `/data` thay vì tạo DB mới. Nếu volume có tên khác, đặt `NOVABANK_SHARED_DATA_VOLUME` trong `.env.hosted` thành tên đó. Compose yêu cầu volume tồn tại trước khi chạy Bank. Xem [thiết kế và quy trình dùng chung DB](SHARED_DATABASE.md).

```sh
docker compose --env-file .env.hosted config --quiet
docker compose --env-file .env.hosted up -d --build
```

Từ mạng được phép, mở `https://<DEMO_DOMAIN>/api/ready` và đợi trạng thái `ready`. Sau đó đăng nhập tài khoản demo trên URL HTTPS, dùng hộp thư lấy mã rồi hỏi số dư trong Assistant. Chia sẻ URL khi luồng này đã chạy qua Caddy. Nếu nhận 403 ngay khi mở trang, xác nhận IPv4 kết nối nằm trong `DEMO_ALLOWED_NETWORKS`. Xem log bằng `docker compose --env-file .env.hosted logs proxy bank agent models`.

Nếu đang dùng cấu hình Basic Auth cũ, chuyển `DEMO_USER` và `DEMO_PASSWORD_HASH` sang `DEMO_ALLOWED_NETWORKS` vì phiên NovaBank dùng header `Authorization`. Nếu subnet Caddy trùng mạng hiện có, đặt cả `NOVABANK_PROXY_SUBNET` và `NOVABANK_PROXY_IP` trong `.env.hosted`. Chế độ review dùng dữ liệu giả và giữ gateway bật. Backup tạo snapshot mã hóa mỗi 24 giờ.

## Prompt Guard cho nguồn ngoài

Agent mặc định dùng model thật để chat và gọi các tool ngân hàng như tra số dư. Các luồng cần quét nguồn ngoài, chẳng hạn đọc nội dung ticket, dừng an toàn nếu Prompt Guard 2 chưa có. Đặt thư mục weights đã được cấp phép trên host rồi thêm cấu hình tùy chọn:

```sh
docker compose -f compose.local.yaml -f compose.prompt-guard.yaml up -d --build
```

Đặt `PROMPT_GUARD_MODEL_DIR` trong `.env` thành đường dẫn tuyệt đối Docker có thể đọc. Image tùy chọn bổ sung runtime CPU, còn weights được mount chỉ đọc. Với máy chủ review, đặt biến trong `.env.hosted` và dùng lệnh:

```sh
docker compose --env-file .env.hosted -f compose.yaml -f compose.prompt-guard.yaml up -d --build
```

Dùng đúng các cờ Compose của stack đang chạy rồi nối `exec bank python -c "from app.agent.promptguard import initialize; print(initialize())"`. Kết quả mong đợi là `available: True`.

## Backup và restore

```powershell
.\backend\.venv\Scripts\python.exe scripts/backup.py keygen --key-file .local/private-backup.key
.\backend\.venv\Scripts\python.exe scripts/backup.py backup --db .local/my-demo.sqlite3 --out .local/backups --key-file .local/private-backup.key
.\backend\.venv\Scripts\python.exe scripts/backup.py restore --archive <archive.backup> --db .local/restored-new.sqlite3 --key-file .local/private-backup.key
.\backend\.venv\Scripts\python.exe scripts/reconcile.py --db .local/restored-new.sqlite3
```

Restore từ chối ghi đè DB/key đang có. Archive chứa consistent SQLite snapshot, per-DB MFA key nếu có và SHA256 manifest. JWT_SECRET hoặc MFA_ENCRYPTION_KEY external phải được giữ riêng. Không chạy bank trỏ DB đang phục hồi.

## CI và release

`.github/workflows/checks.yml` chạy kiểm tra Python, coverage, frontend và Playwright. Job `container-agent` kiểm tra Caddyfile, build từ checkout sạch, tải model nhỏ rồi đi qua đăng nhập, demo inbox và SSE của Agent. Có thể kiểm tra thủ công trên stack demo mới bằng `python scripts/smoke-agent.py --balance` với model mặc định.
