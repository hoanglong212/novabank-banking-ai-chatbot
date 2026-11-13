# Runbook demo Tuần 7: hộp thư giả lập và phiên đo gateway

Áp dụng từ nhánh `week7/fix-outbox-profile-gateway` (R1–R3). Chạy với `ENV=demo`.

## 1. Hộp thư giả lập (`/outbox`)

| Cần đọc | Cách đọc |
|---|---|
| Mã đăng nhập (trước khi có phiên) | Trên màn **Verify sign-in**, bấm link **local demo inbox**. Tab mới chỉ hiện mã của đúng lượt đăng nhập đó (gắn `challenge_id`) |
| Mail sau khi đăng nhập (mã đổi email/số điện thoại, tắt authenticator, thông báo thiết bị mới…) | Bấm **Open demo inbox** trong hộp thoại nhập mã. Tab mới mượn phiên của tab NovaBank và chỉ liệt kê mail của user đó |
| Link xác minh email, link đặt lại mật khẩu | **Không có qua trình duyệt.** Chạy CLI trên máy chạy server (xem dưới) |

Gõ thẳng `/outbox` vào một tab mới sẽ chỉ hiện hướng dẫn. Đây là hành vi đúng: tab đó không có phiên và cũng không có challenge.

### `scripts/dev-outbox.py`

Đọc thẳng file SQLite ở chế độ chỉ đọc. Không có endpoint HTTP nào phục vụ link.

```powershell
# Liệt kê mail (mới nhất trước), có thể lọc theo người nhận
backend\.venv\Scripts\python.exe scripts\dev-outbox.py --db <đường dẫn DB server đang dùng> --email dana@example.test

# Mở một mail: trả code còn hạn và action_url (link xác minh/đặt lại) còn hạn
backend\.venv\Scripts\python.exe scripts\dev-outbox.py --db <DB> --id <id mail> --origin http://127.0.0.1:8080
```

- `--db` là bắt buộc. Ví dụ: `.local/week7-deploy/novabank-v2.sqlite3` khi chạy bằng `scripts/start-week7-local.ps1`.
- `--origin` phải là origin HTTP loopback (`http://127.0.0.1:<cổng>` hoặc `http://localhost:<cổng>`), mặc định `http://127.0.0.1:8080`.
- Mã đã dùng hoặc hết hạn trả `null`.

### Giới hạn cần nói khi demo

- Ai có `challenge_id` thì đọc được mã đăng nhập đó. Trong demo, **lộ mật khẩu thì MFA email không chặn được** (xem `week7-evidence/KNOWN_FAILURES.md`).
- `POST /api/dev/outbox/challenge` bị giới hạn 600 lần / 15 phút cho mỗi địa chỉ IP. Sau Vite proxy, mọi request đều đến từ `127.0.0.1`. Một tab hộp thư ngừng poll sau 5 phút.

## 2. Phiên đo gateway (gateway OFF)

Gateway OFF không còn là công tắc toàn cục. Mỗi lần tắt là một **phiên đo**: chỉ các user được liệt kê, tự hết hạn.

**Giao diện:** đăng nhập `admin` → **Operations → Gateway** → nhập user ở ô *Measure for users* (mặc định `alice, bob`) → **Switch gateway OFF**. Phiên kéo dài 30 phút. Bấm **Switch gateway ON** để đóng sớm.

**API** (token của admin):

```http
PUT /api/admin/agent-gateway   {"enabled": false, "users": ["alice", "bob"], "minutes": 30}
PUT /api/admin/agent-gateway   {"enabled": true}
GET /api/admin/agent-gateway   → gateway, session {users, expires_at, opened_by}, metrics, log_file
```

- Chỉ khi `ENV=demo` hoặc `ENV=lab`. `users`: 1–10 user có thật. `minutes`: 1–120.
- Chỉ run **bắt đầu** trong lúc phiên mở, của user có tên trong phiên, mới có `gateway='off'`. User khác vẫn được bảo vệ.
- Profile `baseline` chỉ dành cho admin khi `ENV` là demo/lab (R2). Khách hàng luôn chạy `defended`.

**Đo tự động:** `tools/gateway_compare.py` tự mở phiên cho `alice, bob, charlie` (120 phút) và bật lại gateway khi xong:

```powershell
backend\.venv\Scripts\python.exe tools\gateway_compare.py --base http://127.0.0.1:8086 --out docs\release\gateway-compare\<ngày>-session
```

Luôn ghi `--out` vào một thư mục mới để không ghi đè kết quả cũ.

### Kiểm tra trước khi demo

1. `GET /api/admin/agent-gateway` phải trả `"session": null` và `"gateway": "on"`.
2. Ghi lại run ID, profile và trạng thái gateway của mọi lượt demo có chuyển tiền (bài học từ sự cố 3/11).
