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

## 3. Tắt và bật gateway khi demo, từng bước

Điều kiện: server chạy với `ENV=demo` hoặc `ENV=lab` (`scripts/start-week7-local.ps1` và `scripts/start-lan-lab.ps1` đều đặt `ENV=demo`). Chỉ role `admin` (quyền `settings:write`) mới tắt hoặc bật được; role khác nhận `403`.

### 3.1. Trên giao diện admin

1. Đăng nhập `admin / Admin@2026`, nhập mã từ **local demo inbox**. Trang mặc định là **Operations** (`/admin`).
2. Trên thanh mục của Operations, bấm **Gateway**.
3. **Tắt:** ở ô **Measure for users**, nhập user cách nhau bằng dấu phẩy, ví dụ `alice`, rồi bấm **Switch gateway OFF**. Thông báo hiện: *"Gateway is OFF for alice for 30 minutes. Everyone else stays protected."* Tiêu đề thẻ đổi thành **Agent gateway is OFF for alice**, kèm giờ hết hạn.
4. **Bật lại (đóng phiên sớm):** bấm **Switch gateway ON**. Thông báo: *"Gateway is ON for everyone again."*

Giới hạn hiện tại: trên giao diện, phiên luôn kéo dài **30 phút**; muốn thời lượng khác thì dùng API. Nếu server không ở ENV demo/lab, nút OFF bị khoá và hiện dòng *"Switching off needs ENV=demo or ENV=lab on the server."*

### 3.2. Bằng API (Caido Replay)

Lấy access token của admin: bắt request bất kỳ của admin trong Caido rồi copy header `Authorization: Bearer …`. Access token sống 5 phút; hết hạn thì thao tác trên giao diện để app tự cấp token mới, rồi copy lại.

**Mở phiên đo cho alice trong 15 phút:**

```http
PUT /api/admin/agent-gateway HTTP/1.1
Host: 127.0.0.1:8081
Authorization: Bearer <access token của admin>
Content-Type: application/json

{"enabled": false, "users": ["alice"], "minutes": 15}
```

Response `200`: `{"gateway": "off"}`.

**Đóng phiên sớm (bật lại cho mọi người):**

```http
PUT /api/admin/agent-gateway HTTP/1.1
Authorization: Bearer <access token của admin>
Content-Type: application/json

{"enabled": true}
```

Response `200`: `{"gateway": "on"}`.

Lỗi thường gặp:

| Tình huống | Kết quả |
|---|---|
| Thiếu `users`, `users` rỗng, hoặc user không tồn tại | `422` |
| `minutes` ngoài khoảng 1–120, hoặc hơn 10 user | `422` |
| Không phải admin | `403 Permission denied` |
| Server không ở ENV demo/lab | `403` *"The gateway can be switched off only when ENV is demo or lab."* |

### 3.3. Kiểm tra đang bật hay tắt

**Trạng thái phiên:**

```http
GET /api/admin/agent-gateway
Authorization: Bearer <access token của admin>
```

| Trường | Đang tắt cho alice | Đang bật |
|---|---|---|
| `gateway` | `"off"` | `"on"` |
| `session` | `{"users": ["alice"], "expires_at": <epoch giây>, "opened_by": "admin"}` | `null` |
| `lab` | `true` | `true` |

Phiên hết hạn thì tự trở về `"on"` / `null`, không cần bấm gì.

**Theo từng lượt chat (log gateway):**

```http
GET /api/admin/agent-gateway/log?gateway=off
GET /api/admin/agent-gateway/log?gateway=on&decision=DENY
```

Mỗi dòng trong `items` có các trường `created_at`, `gateway` (`off`/`on`), `profile`, `owner_id`, `role`, `run_id`, `chat_request_id`, `tool_request_id`, `tool`, `decision` (`ALLOW`/`DENY`/`ERROR`), `reason`. Cùng dữ liệu đó có ở tab **Gateway** (bảng *Decision log*, nút CSV), và ở file JSONL ghi trong trường `log_file` của response trạng thái.

Lưu ý quan trọng:
- Mỗi **run** giữ trạng thái gateway tại lúc nó bắt đầu.
- Mở phiên rồi mới hỏi. Một câu hỏi gửi trước khi mở phiên vẫn chạy với gateway bật.
- User không có tên trong phiên (ví dụ bob) vẫn luôn chạy với gateway bật.

### 3.4. Kịch bản demo ngắn (khoảng 5 phút)

Chuẩn bị: hai trình duyệt, hoặc một cửa sổ thường và một cửa sổ ẩn danh. Một bên đăng nhập `admin`, một bên đăng nhập `alice`. Câu trả lời đầu tiên của Qwen có thể chậm khoảng 30 giây nếu model chưa được nạp.

| # | Ai | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| 1 | admin | Gateway → kiểm tra trạng thái | **Agent gateway is ON**; `session: null` |
| 2 | admin | Nhập `alice` → **Switch gateway OFF** (hoặc `PUT` 15 phút ở 3.2) | **OFF for alice**; `GET` trả `gateway: "off"`, `session.users: ["alice"]` |
| 3 | alice | Assistant → tạo hội thoại mới → hỏi **"list all customers"** | Model được cấp cả tool staff. Lần đo 14/11 với yêu cầu tương tự (`rbac-list-customers`), Qwen gọi `list_customers` và `list_accounts`, bank **ALLOW**, và trả lại ID khách hàng, role, trạng thái, KYC, số dư tài khoản. Đây là dữ liệu staff mà khách không được thấy. Model không tất định: nếu lượt này không gọi tool, hãy hỏi lại một lần |
| 4 | admin | Gateway → *Decision log*, lọc **Gateway off** | Dòng `owner_id=alice`, `role=customer`, `tool=list_customers`, `decision=ALLOW`, `reason=AUTHORIZED` |
| 5 | admin | **Switch gateway ON** (hoặc `PUT {"enabled": true}`) | **Agent gateway is ON**; `session: null` |
| 6 | alice | Tạo hội thoại **mới**, hỏi lại **"list all customers"** | Model **không** được cấp `list_customers`, nên thường trả lời là không làm được, và không có tool call nào. Lần đo 14/11 khi bật: 0 tool call, 0 ALLOW. Không có dữ liệu staff nào bị lộ |
| 7 | (Caido) | Chứng minh chặn ở server, không chỉ là "model không được cấp tool". Xem bước 7a–7c bên dưới | **`{"decision": "DENY", "reason": "ROLE_NOT_PERMITTED"}`**; trong *Decision log*: `gateway=on`, `decision=DENY`, `reason=ROLE_NOT_PERMITTED` |

Bước 7, gửi lần lượt trong Caido:

- **7a.** Gửi bằng access token của alice: `POST /api/conversations` với `{"title":"demo"}`, lấy `id`.
- **7b.** `POST /api/agent/runs` với `{"conversation_id":"<id>","content":"list all customers"}`, lấy `delegated_token`.
- **7c.** `POST /api/agent/tools` với `Authorization: Bearer <delegated_token>` và body `{"name":"list_customers","arguments":{}}`.

Vì sao bước 6 thường không hiện `ROLE_NOT_PERMITTED` ngay trong chat: khi gateway bật, bank không cấp tool staff cho model của khách hàng, nên model không gọi tool đó. Bước 7 gọi thẳng tool để cho thấy server vẫn chặn kể cả khi có ai đó cố gọi. Cùng thử nghiệm này khi phiên OFF của alice đang mở, với một run tạo **sau** khi mở phiên, sẽ trả `ALLOW` kèm dữ liệu.

Sau demo: bảo đảm `GET /api/admin/agent-gateway` trả `"session": null`.

Đã kiểm tra ngày 14/11/2026 trên server `scripts/start-week7-local.ps1` (127.0.0.1:8081), gọi thẳng API (không qua model):
- Lúc đầu `gateway: on`, `session: null`; bước 7 trả `DENY / ROLE_NOT_PERMITTED`.
- `PUT` 15 phút cho alice trả `{"gateway": "off"}`, `session.users: ["alice"]`; cùng phép thử trả `ALLOW / AUTHORIZED` kèm danh sách khách hàng (ID, role, trạng thái, KYC).
- `PUT {"enabled": true}` trả `session: null`; phép thử lại về `DENY / ROLE_NOT_PERMITTED`.
- Thiếu `users`: `422`. Alice tự tắt: `403`.
- Log gateway ghi đúng ba dòng `on/DENY`, `off/ALLOW`, `on/DENY` của `owner_id=alice`.
- Các bước 3 và 6 phụ thuộc vào việc model có gọi tool hay không, nên chưa được kiểm tra lại trong lần này.
