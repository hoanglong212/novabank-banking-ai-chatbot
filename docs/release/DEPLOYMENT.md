# Chạy Agent, chia sẻ bản demo và khôi phục dữ liệu

## Agent từ bản clone mới

Từ thư mục repo, chạy `docker compose -f compose.local.yaml up -d --build` rồi mở <http://127.0.0.1:8080>. Docker Compose khởi động bank, Agent riêng và Ollama nội bộ. Job `models` tải các model còn thiếu, dùng lại weights trong volume ở những lần sau. Hãy chờ job thoát với mã 0 và `/api/ready` báo `ready` trước khi hỏi Agent.

Đăng nhập `alice / Alice@2026`, lấy mã xác thực bằng link demo inbox trên màn hình, rồi vào Assistant hỏi **What is my account balance?**. Máy chạy Docker cần internet ở lần build và tải weights đầu. Bộ mặc định gồm Qwen 7B, Llama 3B và Nomic embeddings. Dành khoảng 7 GB cho weights ngoài dung lượng image và nên có 16 GB RAM cho host. Thời gian phản hồi phụ thuộc CPU/GPU.

- Tải model hoặc lỗi startup: `docker compose -f compose.local.yaml logs models ollama agent bank`. Sau khi xử lý, chạy lại lệnh `up`. `models` ở trạng thái `Exited (0)` là bình thường.
- Port bận: đặt `NOVABANK_PORT=8081` trong file `.env` ở root và mở <http://127.0.0.1:8081>.
- Có thể chọn model bằng các biến trong [.env.example](../../.env.example). Giữ model mặc định khi cần so với kết quả nghiên cứu. `LLM_PROVIDER=mock` là phản hồi demo có nhãn, bỏ qua tải weights.
- `docker compose -f compose.local.yaml down` dừng stack và giữ cả dữ liệu SQLite lẫn weights. Chạy lại `up -d --build` sau khi pull bản mới.

## Chạy native trên Windows

Sau khi cài Python, Node.js và Ollama, chạy các lệnh dưới đây từ thư mục repo. Lần đầu thêm `-Setup` để cài dependencies cho launcher. Chuẩn bị model bằng Ollama trước khi chạy `-Mode ollama`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Mode ollama
```

Launcher build frontend rồi chạy Banking API :8080 và agent riêng :8093; Ctrl+C dừng cả hai. `-Mode mock` chạy offline và luôn ghi rõ no model. Không tự cài dependencies, model hoặc dịch vụ. `.env.example` mô tả cấu hình. Model đã dùng trong nghiệm thu: `qwen2.5:7b`, `llama3.2:3b`, embedding `nomic-embed-text:latest` trên Ollama hiện có.

Với DB phong phú mới, không thay DB cũ:

```powershell
.\backend\.venv\Scripts\python.exe scripts/seed-demo.py --out .local/my-demo.sqlite3
.\backend\.venv\Scripts\python.exe scripts/serve.py --db .local/my-demo.sqlite3
```

Seed từ chối target đã tồn tại. Tạo 5 customer, 6 tháng dữ liệu giả, 10 thẻ, 20 hóa đơn và 5 savings. Bảy history legacy từ seed gốc vẫn được phân biệt với ledger snapshots mới.

## Chia sẻ qua HTTPS

Trên máy chủ Linux của nhóm, chạy Docker Engine với Compose v2. Trỏ bản ghi DNS A về IPv4 của máy chủ, mở 80/443 cho Caddy và điền cấu hình trong file `.env` riêng trên host. Chọn IPv4 hoặc CIDR của nhóm review hay mạng VPN. Caddy so địa chỉ kết nối trực tiếp, vì vậy dùng cấu hình này khi Caddy nhận kết nối từ trình duyệt. Nếu đặt sau proxy khác, cần cấu hình kiểm soát truy cập tại proxy đó trước khi chia sẻ URL.

```
DEMO_DOMAIN=your-demo-host.example
ACME_EMAIL=your-operator-email
DEMO_ALLOWED_NETWORKS="203.0.113.10/32 198.51.100.0/24"
JWT_SECRET=<persistent random secret>
BACKUP_KEY_FILE=/absolute/path/to/private-backup.key
```

Thay địa chỉ ví dụ bằng địa chỉ thực của nhóm. Nếu đang dùng bản triển khai Basic Auth cũ, thay `DEMO_USER` và `DEMO_PASSWORD_HASH` bằng `DEMO_ALLOWED_NETWORKS`. NovaBank dùng header `Authorization` cho token phiên, nên dùng giới hạn mạng ở Caddy. Chỉ dùng tài khoản và dữ liệu giả trong môi trường review. Chế độ `review` cho phép demo inbox có xác thực và giữ gateway bật.

Tạo secret JWT bằng `openssl rand -hex 32`. Tạo key backup bằng `python scripts/backup.py keygen --key-file <new-private-key-path>` trên máy đã có dependencies của repo. Với Docker rootful, đặt file ở thư mục riêng và cấp quyền đọc cho UID 10001 của container backup, ví dụ owner 10001 và mode 0400. Giữ `.env` và key ngoài Git.

```sh
docker compose config --quiet
docker compose up -d --build
```

Khi Caddy có chứng chỉ và healthcheck bank đạt, chia sẻ `https://<DEMO_DOMAIN>` với nhóm trong mạng đã cho phép. Người dùng chỉ cần trình duyệt. Caddy là cổng duy nhất mở ra ngoài và stream SSE đến trình duyệt. Bank chỉ tin địa chỉ chuyển tiếp từ IP riêng của Caddy để giới hạn đăng nhập theo địa chỉ truy cập. Nếu subnet Docker của Caddy trùng mạng hiện có, đặt cặp `NOVABANK_PROXY_SUBNET` và `NOVABANK_PROXY_IP` trong `.env`. Bank giữ SQLite, Agent gọi API nội bộ bằng token giới hạn và Ollama dùng volume riêng. Backup tạo snapshot mã hóa mỗi 24 giờ.

## Prompt Guard cho nguồn ngoài

Agent mặc định dùng model thật để chat và gọi các tool ngân hàng như tra số dư. Các luồng cần quét nguồn ngoài, chẳng hạn đọc nội dung ticket, dừng an toàn nếu Prompt Guard 2 chưa có. Đặt thư mục weights đã được cấp phép trên host rồi thêm cấu hình tùy chọn:

```sh
docker compose -f compose.local.yaml -f compose.prompt-guard.yaml up -d --build
```

Đặt `PROMPT_GUARD_MODEL_DIR` trong `.env` thành đường dẫn tuyệt đối có thể đọc từ Docker. Image tùy chọn bổ sung runtime CPU, còn weights được mount chỉ đọc. Với máy chủ review, thay `compose.local.yaml` bằng `compose.yaml`. Xác nhận bộ quét đã nạp bằng `docker compose -f compose.local.yaml -f compose.prompt-guard.yaml exec bank python -c "from app.agent.promptguard import initialize; print(initialize())"`. Kết quả mong đợi là `available: True`.

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
