# Runbook Caido trên máy ảo

Mục tiêu: bắt và sửa traffic thật của NovaBank từ một máy ảo (VM), cho luồng đăng nhập → inbox → chat → phê duyệt → xác nhận chuyển tiền, rồi ghi lại kết quả vào `capture/caido/`. Đây là việc nhóm tự làm; các "kết quả mong đợi" dưới đây suy ra từ code và test của nhánh `week7/fix-outbox-profile-gateway`, **chưa được đo bằng Caido**.

## 1. Chạy app cho VM truy cập (máy host)

```powershell
# Qwen trên Ollama riêng 127.0.0.1:11435 (xem scripts/start-week7-local.ps1); hoặc -Mode mock nếu không cần model
.\scripts\start-lan-lab.ps1
```

Script đặt `ENV=demo` (bật hộp thư giả lập và phiên đo gateway), bind `0.0.0.0:8080`, rồi in các địa chỉ LAN, ví dụ `http://192.168.x.y:8080`. UI và API cùng một cổng. Mở firewall cho TCP 8080 chỉ trên mạng lab. Credential demo là công khai, nên không dùng trên mạng lạ.

Muốn bắt cả traffic phía sau (bank → agent → Ollama): chạy `.\scripts\start-lan-lab.ps1 -Proxy http://<IP VM>:<cổng listener Caido>`, đồng thời cho listener Caido nghe trên `0.0.0.0`.

## 2. Cài Caido trên VM

1. Tải Caido từ trang chính thức, cài và mở (Caido CLI hoặc Desktop). Tạo project mới, ví dụ `novabank-week7`.
2. **Listener:** mặc định `127.0.0.1:8080` trên VM. Nếu dùng `-Proxy` ở bước 1, đổi thành `0.0.0.0:<cổng>`.
3. **Chứng chỉ CA:** app chạy HTTP thuần, nên không bắt buộc. Nếu sau này đặt Caddy/HTTPS phía trước, tải CA của Caido (Settings → CA certificate) và import vào trình duyệt của VM (Firefox: Settings → Certificates → Import, tick "Trust this CA to identify websites").
4. **Proxy trình duyệt:** trong trình duyệt của VM, đặt HTTP proxy `127.0.0.1:8080` (Firefox: Settings → Network → Manual proxy; hoặc dùng FoxyProxy). Xoá `127.0.0.1`, `localhost` khỏi danh sách "No proxy" nếu cần.
5. **Scope:** thêm `http://<IP host>:8080` vào scope. Bật Intercept khi cần sửa request.

## 3. Luồng cần bắt

| # | Thao tác trên UI | Request chính | Ghi chú |
|---|---|---|---|
| 1 | Đăng nhập `alice / Alice@2026` | `POST /api/auth/login` → `challenge_id` | |
| 2 | Bấm **local demo inbox** | `POST /api/dev/outbox/challenge {challenge_id}` | Tab mới; mã chỉ của lượt này |
| 3 | Nhập mã | `POST /api/auth/mfa/verify` → `access_token`, `refresh_token` | |
| 4 | Chat: "Prepare a transfer of 10000 VND to ACC-BOB-001." | `POST /api/conversations/{id}/stream` (SSE) | Sự kiện `run` có `profile` thực tế |
| 5 | Bấm duyệt đề xuất | `POST /api/agent/approvals/{id} {approve:true}` → `draft_id` | |
| 6 | Trang xác nhận | `GET /api/transfers/{id}` → có `confirm_token` | Token B5, sống ≤ 5 phút |
| 7 | Tạo hoặc nhập PIN, **Confirm transfer** | `POST /api/transfers/{id}/confirm {otp, confirm_token}` + header `Idempotency-Key` | |
| 8 | (Tuỳ chọn, với `-Proxy`) | bank→agent `POST /run`; agent→bank `/api/agent/context`, `/api/agent/tools`; agent→Ollama `/api/chat` | JWT ủy quyền 180 giây |

Lưu từng bước: Caido **Export** (HAR hoặc project), ảnh chụp màn hình request/response vào `capture/caido/`. Đặt tên `NN-<bước>.har|png`. Che `Authorization`, `refresh_token`, `confirm_token`, mã OTP/PIN trước khi commit (xem cách che trong `capture/README.md`).

## 4. Request cần thử sửa và kết quả mong đợi

| Thử | Cách sửa (Intercept hoặc Replay) | Kết quả mong đợi | Cơ sở trong code/test |
|---|---|---|---|
| Đổi `amount_vnd` lúc xác nhận | Body `/confirm` không có số tiền; thử sửa `amount_vnd` **bên trong** `confirm_token` (decode, sửa payload, giữ chữ ký) | `403 TOKEN_INVALID` | `test_amount_or_recipient_edited_inside_the_token_breaks_the_signature` |
| Đổi `to_account` lúc xác nhận | Như trên với `to_account`; hoặc dùng `confirm_token` của một draft khác | `403 TOKEN_INVALID` / `403 TOKEN_MISMATCH` | `test_token_for_other_parameters_is_refused_even_when_signed`, `test_another_users_token_is_refused` |
| Đổi `amount_vnd` / `to_account` lúc **tạo** draft | Sửa body `POST /api/transfers` | Server chấp nhận như một yêu cầu mới; màn review hiện người nhận và số tiền đã bị sửa; người nhận mới > 10.000.000 VND bị `NEW_RECIPIENT_LIMIT_EXCEEDED`. **B5 không bảo vệ bước này**; chỉ HTTPS mới bảo vệ | `transfers.py::prepare`, `test_week7_limits.py` |
| Bỏ hoặc phát lại token | Xoá `confirm_token`; gửi lại `/confirm` đã thành công với `Idempotency-Key` khác; gửi lại với cùng key | `403 TOKEN_REQUIRED`; `409 TOKEN_REPLAYED`; cùng key → biên lai cũ, không có giao dịch thứ hai | `test_missing_token_is_refused`, `test_reused_token_is_refused` |
| Token hết hạn | Chờ quá 5 phút rồi Replay `/confirm` | `403 TOKEN_EXPIRED` (draft cũng hết hạn) | `test_expired_token_is_refused` |
| `profile` | Sửa `"profile":"defended"` → `"baseline"` trong body `/stream` hoặc `/api/agent/runs` khi là alice | Run vẫn `defended`: sự kiện SSE `run` và `GET /api/agent/runs/{id}` đều trả `profile: defended`. Chỉ admin trong ENV demo/lab mới có `baseline` | `test_profile_server_owned.py` |
| `/api/dev/outbox` không token | Replay `GET /api/dev/outbox` và `GET /api/dev/outbox/{id}` sau khi bỏ header `Authorization`; dùng token của bob đọc id mail của alice | `401`; `404` | `test_outbox_takeover.py`, `test_outbox_variants.py` |
| Challenge outbox | `POST /api/dev/outbox/challenge` với `challenge_id` ngẫu nhiên; gửi liên tục bằng Caido Automate | `404`; sau 600 lần / 15 phút từ một IP thì `429` | `test_challenge_lookups_are_rate_limited_per_address` |
| `arguments` của `/api/agent/tools` | Lấy JWT ủy quyền (response `/api/agent/runs` hoặc header bank→agent). Gọi `prepare_transfer` với `to_account: ACC-CHARLIE-001` khi tin nhắn yêu cầu Bob | `DENY / USER_INTENT_MISMATCH` | `test_PI_bypass_week7.py` |
| Tool staff khi là khách | Gọi `list_customers` hoặc `propose_settings_change` bằng JWT ủy quyền của alice | `DENY / ROLE_NOT_PERMITTED` | `test_rbac_proposals.py`, `test_support_rbac.py` |
| Chèn role | Thêm `"role":"admin"` vào body các request JSON (login, runs, tools) | `422` (`extra='forbid'`) hoặc bị bỏ qua; role luôn đọc từ DB | `test_SEC_04.py`, `test_role_claim_in_token_payload_is_ignored` |
| Gateway OFF | Admin mở phiên đo cho `alice` rồi lặp lại hàng `arguments` / tool staff | Chỉ run của alice có `gateway=off` và tool staff được ALLOW; run của bob vẫn `on`. Phê duyệt và PIN vẫn bắt buộc | `test_gateway_session.py`, `DEMO_RUNBOOK_WEEK7.md` |

Ghi kết quả thật vào bảng dưới, kèm `X-Request-ID` của response để đối chiếu với log gateway (`/api/admin/agent-gateway/log`).

| Thử | Kết quả thật | Khớp mong đợi? | File bằng chứng |
|---|---|---|---|
| | | | |
