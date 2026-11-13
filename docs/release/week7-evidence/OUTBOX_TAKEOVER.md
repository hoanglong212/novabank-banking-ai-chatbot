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
