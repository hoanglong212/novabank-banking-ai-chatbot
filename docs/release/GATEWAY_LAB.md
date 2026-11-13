# Lab gateway: Caido/Burp từ máy ảo, công tắc gateway và log ALLOW/DENY

Chỉ dùng cho demo/lab. Không bật trên môi trường thật.

## 1. Mở app và API agent ra mạng

```powershell
# Trên máy host (Windows), trong thư mục repo
.\.local\local-deploy\start-lan.ps1
```

Script đặt `ENV=demo` và chạy `scripts/run-demo.ps1 -Lan`. Bank và agent nghe trên `0.0.0.0`. Khi chạy, nó in ra địa chỉ dùng được, ví dụ:

```
network: app http://192.168.100.113:8080  agent API http://192.168.100.113:8093
network: app http://172.30.48.1:8080      agent API http://172.30.48.1:8093
```

Dùng IP nào tuỳ cách máy ảo nối mạng: bridged thì dùng IP LAN, Hyper-V Default Switch hoặc WSL thì dùng IP vEthernet.

**Firewall (chạy một lần, PowerShell quyền Administrator).** Card Ethernet đang ở profile Public, và Windows có sẵn rule *Block python.exe* cho Public. Rule Block luôn thắng rule Allow, nên phải tắt rule đó rồi mở hai port, và chỉ mở cho subnet nội bộ:

```powershell
Get-NetFirewallRule -DisplayName 'python.exe' | Where-Object Action -eq Block | Disable-NetFirewallRule
New-NetFirewallRule -DisplayName 'NovaBank lab 8080/8093' -Direction Inbound -Protocol TCP -LocalPort 8080,8093 -RemoteAddress LocalSubnet -Action Allow
```

Gỡ sau khi xong: `Remove-NetFirewallRule -DisplayName 'NovaBank lab 8080/8093'`. Có thể bật lại rule python bằng `Enable-NetFirewallRule`.

Cảnh báo: chế độ LAN mở cả `/outbox` cho mọi máy cùng mạng. Từ 13/11, outbox chỉ trả mail của user đang đăng nhập, hoặc mã đăng nhập gắn với `challenge_id` của chính lượt đăng nhập đó; link xác minh/đặt lại chỉ đọc bằng `scripts/dev-outbox.py` (xem `week7-evidence/OUTBOX_TAKEOVER.md`). Vẫn chỉ dùng trong mạng lab.

## 2. Bắt traffic bằng Caido hoặc Burp trong máy ảo

**Trình duyệt → bank.** Trong máy ảo, đặt proxy của trình duyệt về Caido/Burp (ví dụ `127.0.0.1:8080` của Burp), rồi mở `http://<IP host>:8080`. Mọi request `/api/*` của app đi qua proxy. App dùng http thường; key chống lặp đã chuyển sang `crypto.getRandomValues` nên chạy được ngoài localhost.

**Gọi thẳng API agent.** `http://<IP host>:8093/run` cần header `Authorization: Bearer <delegated_token>`. Token này lấy từ `POST /api/agent/runs` và hết hạn sau 180 giây. API tool của bank là `POST /api/agent/tools` với cùng token. Dùng Repeater hoặc Replay để thử tham số.

**Traffic nội bộ (bank ↔ agent ↔ Ollama).** Muốn thấy cả các kênh này, cho Burp/Caido trong máy ảo nghe trên interface mạng (ví dụ `0.0.0.0:8081`), rồi chạy:

```powershell
.\.local\local-deploy\start-lan.ps1 -Proxy http://<IP máy ảo>:8081
```

Khi đó bank→agent, agent→bank (`/api/agent/context`, `/api/agent/tools`, `/api/agent/finish`) và lời gọi tới Ollama đều đi qua proxy.

## 3. Công tắc gateway

Bật/tắt tại **Operations → Gateway** (chỉ admin), hoặc qua API:

```http
PUT /api/admin/agent-gateway      {"enabled": false, "users": ["alice", "bob"], "minutes": 30}   # mở phiên đo
PUT /api/admin/agent-gateway      {"enabled": true}    # đóng phiên đo, bật lại cho mọi người
GET /api/admin/agent-gateway      # trạng thái, phiên đang mở + số liệu off/on
```

Từ 13/11 (R3), tắt gateway **không còn là công tắc toàn cục**. Mỗi lần tắt là một phiên đo, chỉ áp dụng cho các user được liệt kê (tối đa 10 user, phải tồn tại), và tự hết hạn sau `minutes` (1–120, mặc định 30). User khác vẫn được bảo vệ trong lúc đo. Giá trị `"off"` toàn cục kiểu cũ trong database bị bỏ qua. Server chỉ cho mở phiên đo khi `ENV=demo` hoặc `ENV=lab`. Ở môi trường khác, gateway luôn bật kể cả khi database có phiên đo. Mỗi lần đổi được ghi vào banking audit. Mỗi run giữ trạng thái gateway lúc nó bắt đầu (cột `agent_runs.gateway`).

| | Gateway ON | Gateway OFF |
|---|---|---|
| Lọc prompt đầu vào (`inspect_prompt`) | có | bỏ (vẫn ghi log) |
| Danh sách tool theo role | có | model được đưa mọi tool |
| Kiểm tra role, ràng buộc với yêu cầu mới nhất | có | bỏ |
| Kiểm tra proposal (người nhận, số tiền, ticket, nội dung trả lời) | có | bỏ, lưu nguyên tham số của model |
| Source guard (cách ly dữ liệu bị chèn lệnh) | có | bỏ |
| Dừng sau 2 lần DENY | có | bỏ |
| Lọc câu trả lời đầu ra | có | bỏ, lưu nguyên văn |
| Đăng nhập, phiên, token uỷ quyền | có | **giữ** |
| Che OTP/mật khẩu, kiểm tra schema, tối đa 8 lời gọi | có | **giữ** |
| Truy vấn dữ liệu theo chủ sở hữu | có | **giữ** |
| Duyệt của người dùng + OTP/PIN, kiểm tra role khi duyệt | có | **giữ** |

Vì vậy, khi gateway OFF mà "tấn công thành công", nghĩa là bank đã cho tool chạy hoặc đã tạo proposal. Tiền chỉ chuyển khi chủ tài khoản tự duyệt và nhập OTP.

## 4. Log ALLOW/DENY cho từng request

Mỗi lời gọi tool của agent được ghi một dòng gồm: thời gian, gateway on/off, profile, user, role, run, `chat_request_id`, `tool_request_id`, thứ tự, tool, ALLOW/DENY/ERROR, lý do, độ trễ.

- **Database:** bảng `agent_calls` nối với `agent_runs`. Xem ở tab Gateway, hoặc `GET /api/admin/agent-gateway/log?gateway=off&decision=DENY`.
- **CSV:** `GET /api/admin/agent-gateway/log.csv`, hoặc nút CSV trong tab Gateway.
- **File JSONL (để `tail` trong lúc test):** `<DB_PATH>.gateway.jsonl`. Với launcher local là `.local/local-deploy/novabank.sqlite3.gateway.jsonl`. File này ghi cả lần bộ lọc prompt chặn (`tool=input_guard`).

```powershell
Get-Content .local\local-deploy\novabank.sqlite3.gateway.jsonl -Wait -Tail 20
```

**Đối chiếu với Caido/Burp:** mỗi response có header `X-Request-ID`. `chat_request_id` là request gửi tin nhắn (`/api/conversations/{id}/stream`). `tool_request_id` là request `POST /api/agent/tools` của agent. ERROR chỉ xuất hiện khi gateway OFF, lúc một tool bị gọi vào chỗ code không lường trước (ví dụ staff gọi tool của khách). ERROR không tính là ALLOW hay DENY.

## 5. Ra số liệu "gateway tắt so với bật"

```powershell
backend\.venv\Scripts\python.exe tools/gateway_compare.py --base http://<IP host>:8080 [--proxy http://127.0.0.1:8081] [--reps 3]
```

Script chỉ dùng HTTP, nên chạy được trong máy ảo qua Burp/Caido. Nó tự đăng nhập bằng outbox demo, chạy cùng bộ kịch bản ở OFF rồi ở ON, và bật lại gateway khi xong. Bộ kịch bản gồm:

- Tấn công trực tiếp lấy từ `research/scenarios.py`.
- 6 prompt leo thang quyền (khách đòi tool staff/admin).
- 10 tác vụ hợp lệ, dùng để đo utility.

Kết quả ghi vào `docs/release/gateway-compare/`:

- `results.csv`: mỗi run một dòng, gồm request ID, chuỗi tool ALLOW/DENY, tool nhạy cảm được cho qua và proposal đang chờ.
- `summary.md`: bảng OFF/ON gồm ASR, ASR leo thang quyền, utility, tổng ALLOW/DENY/ERROR, và kiểm tra trạng thái tài khoản không đổi.
