# Local, container và khôi phục

**Phạm vi đã chốt ngày 01/11/2026: chỉ chạy local.** Dùng launcher bên dưới; không cần VPS, tên miền hoặc Docker. Phần container/HTTPS và CI remote là hướng dẫn tùy chọn cho tương lai, không phải điều kiện nghiệm thu hiện tại.

## Chạy local một lệnh

Khi dependencies của repo đã có, từ PowerShell tại repo:

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

## HTTPS bằng Docker Compose/Caddy

`compose.yaml` có bank, agent, proxy và backup. Agent không mount DB, không nhận JWT secret. Chỉ Caddy mở 80/443. Cần Docker Engine đang chạy, VPS/domain thực, DNS/firewall phù hợp và người vận hành cung cấp các biến sau vào môi trường hoặc file `.env` cục bộ:

```
DEMO_DOMAIN=your-demo-host.example
ACME_EMAIL=your-operator-email
DEMO_USER=reviewer
DEMO_PASSWORD_HASH=<Caddy bcrypt hash>
JWT_SECRET=<persistent random secret>
BACKUP_KEY_FILE=<separate existing Fernet key file>
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
```

Tạo key bằng `python scripts/backup.py keygen --key-file <new-private-key-path>`. Hash gateway password bằng Caddy `hash-password` trong môi trường vận hành. Không commit secret hay key. Cấu hình dùng Ollama trên host qua `host.docker.internal`; Linux cần Ollama bind vào interface Docker có thể truy cập, giới hạn firewall với host. Không expose Ollama public.

Chạy `docker compose config --quiet` trước `docker compose up --build -d`. `/api/ready` và agent `/health` phục vụ healthcheck. Proxy không buffer SSE. Backup tạo snapshot mã hóa mỗi 24 giờ, retry sau 5 phút nếu lỗi. Archive không tự xóa; người vận hành đặt retention sau khi kiểm tra khả năng restore. Volume tạo mới có UID 10001 phù hợp image bank/backup.

**Đã kiểm tra:** Compose parse, Dockerfile/source paths, local two-process serving, backup/restore thực tế. **Chưa kiểm tra:** build/run image do Docker Engine chưa chạy; DNS/ACME/VPS/HTTPS public chưa có môi trường. Không xem cấu hình hợp lệ là đã deploy.

## Backup và restore

```powershell
.\backend\.venv\Scripts\python.exe scripts/backup.py keygen --key-file .local/private-backup.key
.\backend\.venv\Scripts\python.exe scripts/backup.py backup --db .local/my-demo.sqlite3 --out .local/backups --key-file .local/private-backup.key
.\backend\.venv\Scripts\python.exe scripts/backup.py restore --archive <archive.backup> --db .local/restored-new.sqlite3 --key-file .local/private-backup.key
.\backend\.venv\Scripts\python.exe scripts/reconcile.py --db .local/restored-new.sqlite3
```

Restore từ chối ghi đè DB/key đang có. Archive chứa consistent SQLite snapshot, per-DB MFA key nếu có và SHA256 manifest. JWT_SECRET hoặc MFA_ENCRYPTION_KEY external phải được giữ riêng. Không chạy bank trỏ DB đang phục hồi.

## CI và release

`.github/workflows/checks.yml` chạy compile, full pytest với financial line coverage ≥80%, component tests, build và Playwright Chromium. Có artifact test results/coverage. Chưa có GitHub Actions run cho thay đổi hiện tại; lệnh đọc remote trả danh sách rỗng. Chưa commit/push/tag v1.0. Bản local và release evidence được tách trong [STATUS](STATUS.md).
