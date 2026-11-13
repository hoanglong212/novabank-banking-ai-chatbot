# R1 — Chiếm tài khoản qua hộp thư demo (`/api/dev/outbox`)

Ngày 13/11/2026. Nguồn: `BAO-CAO-KIEM-TRA-TUAN-7.md`, mục R1. Ghi lại **trước khi sửa** ở commit `21813d4`.

## Điều kiện

- Server chạy với `ENV=demo`. Đây là cấu hình demo LAN: `compose.local.yaml`, và `tools/gateway_compare.py` yêu cầu `ENV=demo`.
- Kẻ tấn công chỉ cần biết **username**. Email của user demo đoán được: `<username>@novabank.test` (`backend/app/identity_schema.py:36`).
- Không cần mật khẩu, OTP, JWT hay quyền truy cập máy chủ.

## Nguyên nhân

`backend/app/api/routes/dev.py` (trước khi sửa):

- `GET /api/dev/outbox` không có dependency xác thực, trả 50 email mới nhất của **mọi** user.
- `GET /api/dev/outbox/{id}` trả `code` (OTP) và `action_url` (link xác minh hoặc đặt lại mật khẩu, có token) của bất kỳ email nào.
- Chỉ người nhận bị che. Loại email (`RESET_PASSWORD`, `LOGIN_OTP`, …) và thứ tự thời gian vẫn đủ để chọn đúng email.

## Chuỗi tấn công

Mọi request ở bước 1–4 đều **không có header `Authorization`**.

| # | Request | Kết quả |
|---|---|---|
| 1 | `POST /api/auth/forgot-password` `{"email":"alice@novabank.test"}` | `202`. Server ghi email `RESET_PASSWORD` cho Alice vào outbox |
| 2 | `GET /api/dev/outbox` → lấy `id` mới nhất, rồi `GET /api/dev/outbox/{id}` | `200`, `action_url = "/#reset-password?token=<token>"` |
| 3 | `POST /api/auth/reset-password` `{"token":"<token>","password":"<mật khẩu mới>"}` | `200`. Mật khẩu Alice bị đổi, mọi phiên cũ của Alice bị huỷ |
| 4 | `POST /api/auth/login` (mật khẩu mới) → `challenge_id`; đọc email `LOGIN_OTP` mới nhất như bước 2; `POST /api/auth/mfa/verify` | `202`, `200`. Kẻ tấn công có access token của Alice |
| 5 | `POST /api/auth/pin` `{"password":"<mật khẩu mới>","pin":"135790"}` (với token vừa lấy) | `200`. Kẻ tấn công biết mật khẩu nên tự đặt được PIN giao dịch |
| 6 | `POST /api/transfers` `{"to_account":"ACC-CHARLIE-001","amount_vnd":5000000}`, rồi `POST /api/transfers/{id}/confirm` `{"otp":"135790"}` | `201`, `200 COMPLETED`. Đã chuyển 5.000.000 VND sang Charlie |

5.000.000 VND nằm dưới hạn mức người nhận mới (10.000.000 VND), nên không bị lớp giới hạn thiệt hại chặn. Nếu Alice không cài PIN, OTP chuyển tiền gửi qua email cũng đọc được từ cùng outbox ở bước 2.

**Hệ quả:** MFA bằng email, OTP chuyển tiền và quy trình đặt lại mật khẩu đều mất tác dụng khi `ENV=demo`. Mọi tài khoản demo có thể bị chiếm và rút tiền tới hạn mức.

## Tái hiện

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q tests/test_outbox_takeover.py
```

`tests/test_outbox_takeover.py::test_anonymous_outbox_takeover_chain` chạy đủ 6 bước trên một SQLite tạm và khẳng định giao dịch `COMPLETED`. Trước khi sửa, test **pass**. Sau khi sửa, test được đánh dấu `xfail(strict=True)`: nó phải thất bại, và nếu lỗ hổng quay lại thì test pass ngoài dự kiến, làm suite báo đỏ.

## Cách sửa

Xem commit tiếp theo trên nhánh `week7/fix-outbox-profile-gateway`:

- Outbox chỉ trả email của user đang đăng nhập.
- Mã đăng nhập trước khi có phiên chỉ đọc được bằng `challenge_id` mà người đăng nhập đang giữ.
- Link xác minh email và link đặt lại mật khẩu không còn phục vụ qua HTTP. Chỉ đọc được bằng `scripts/dev-outbox.py` trên máy chạy server.

## Sau khi sửa (14/11/2026)

Sửa ở commit `b2b9e1b` (outbox theo user/challenge), `504c735` (rate limit cho challenge, kiểm tra origin của tab opener). Chạy lại 6 bước trên SQLite tạm, `ENV=demo`, bằng `TestClient` (script replay, không gửi request ra ngoài):

| # | Request | Trước sửa | Sau sửa |
|---|---|---|---|
| 1 | `POST /api/auth/forgot-password` (Alice) | `202` | `202`. Không đổi, có chủ đích: response giống hệt cho email có hoặc không tồn tại |
| 2 | `GET /api/dev/outbox` không token | `200`, liệt kê mail mọi user | **`401 Please sign in`**. Chuỗi tấn công dừng ở đây |
| 2b | `GET /api/dev/outbox/{id của mail reset}` không token, kể cả khi biết id | `200`, có `action_url` kèm token | **`401`** |
| 3 | `POST /api/auth/reset-password` (không có token thật) | `200` | **`400`** link không hợp lệ |
| 4 | Đăng nhập Alice bằng mật khẩu của kẻ tấn công | `202` | **`401`**, mật khẩu không bị đổi |
| 5 | Đặt PIN bằng phiên chiếm được | `200` | Không thực hiện được (không có phiên) |
| 6 | Chuyển 5.000.000 VND cho Charlie | `COMPLETED` | Không thực hiện được |

Test tái hiện `tests/test_outbox_takeover.py::test_anonymous_outbox_takeover_chain` giờ là `xfail(strict=True)`: nó dừng ở bước 2 và phải luôn thất bại.

### Ba biến thể

| Biến thể | Kết quả | Test |
|---|---|---|
| (1) Đăng nhập bằng Charlie rồi đọc outbox, trong khi Alice và Bob đang có mã đăng nhập còn hạn | Danh sách chỉ có mail của Charlie. Mọi mail của người khác, đọc theo id, trả `404` | `tests/test_outbox_variants.py::test_charlie_sees_only_charlies_mail` |
| (2) `challenge_id` sai, của người khác, hết hạn; gọi liên tục | Sai: `404`. Challenge của Bob chỉ trả mail của Bob. Mã đã hết hạn: `code=null`. Vượt hạn mức theo IP: `429` (giá trị thật 600 lần / 15 phút; test hạ xuống để kiểm tra) | `test_wrong_foreign_or_expired_challenges_are_refused_then_rate_limited`, `tests/test_outbox_takeover.py::test_challenge_lookups_are_rate_limited_per_address` |
| (3) Link reset của Alice có lộ qua endpoint HTTP nào không | Gọi **mọi** route GET của app (tham số đường dẫn thay bằng id mail reset) với 4 vai trò: ẩn danh, bob, charlie, admin; mỗi route × vai trò một request. Route đọc duy nhất bằng POST (`/api/dev/outbox/challenge`) chỉ truy vấn `kind='LOGIN_OTP'` theo challenge, và mail reset không có `challenge_id`. Token không xuất hiện trong bất kỳ response nào. Link chỉ đọc được bằng `scripts/dev-outbox.py` trên máy chạy server | `test_alices_reset_link_is_not_served_by_any_http_endpoint` |

Lệnh: `cd backend && .venv/Scripts/python.exe -m pytest -q tests/test_outbox_takeover.py tests/test_outbox_variants.py`. Kết quả ngày 14/11: 3 passed ở `test_outbox_variants.py`.

### Giới hạn còn lại

Ai giữ `challenge_id` thì đọc được mã đăng nhập đó. `challenge_id` chỉ được trả cho người vừa nhập đúng mật khẩu, nên **trong demo, lộ mật khẩu nghĩa là MFA email không chặn được**: kẻ có mật khẩu đăng nhập, nhận challenge, rồi tự đọc mã. Đây là giới hạn của hộp thư giả lập, không phải của email thật. Xem `KNOWN_FAILURES.md`.
