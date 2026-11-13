# Week 7 — ủy quyền mật mã và giới hạn

```text
Password + MFA
      ↓
Access JWT (sub, sid, ver) → database role + active session
      ↓
User intent → bank binds arguments → encrypted bound_request_json
      ↓
Delegated JWT (aud=novabank-agent-tools, run, sub, sid, ver, exp=180s)
      ↓
Isolated agent → bank tool endpoint → role / intent / ownership / budget checks
      ↓
PENDING approval → same customer session approves → PENDING_OTP draft
      ↓
Signed transfer token (aud=transfer-confirm, sub=draft, owner, recipient, amount, exp ≤ 5 min, jti)
      ↓
Bank confirmation + token + OTP/PIN + idempotency → atomic ledger posting, jti spent
```

JWT scopes remain `ai:read` and `ai:prepare`; they never include confirmation. Staff capability sets are narrower than these token labels: the bank checks the current database role on each delegated request. A valid signature does not mean every tool is allowed. Cancellation, expired runs and revoked sessions invalidate use of a delegation.

Intent encryption protects stored contents; independent binding determines authorization. Neither encryption alone nor an LLM classifier guarantees correct authorization. There is a useful analogy to control/data separation and capabilities in [CaMeL](https://arxiv.org/abs/2503.18813), but this repository does not implement CaMeL's full information-flow system or inherit its formal guarantee.

| Tấn công / sự cố | Lớp kiểm soát | Giới hạn |
|---|---|---|
| Nguồn ngoài yêu cầu đổi recipient/amount | Binding tại bank, customer review | Người dùng vẫn cần xem đúng nội dung |
| Customer tự nhận là admin | Database role, tool allowlist | JWT/session thực sự bị chiếm cần thu hồi |
| Lộ delegated token | 180s, audience/run/session/version, budgets, no confirm | Read data trong phạm vi token có thể còn khả dụng tới khi hết hạn/thu hồi |
| Replay xác nhận | OTP gắn draft, consumed secret, idempotency, transaction lock | Không thay thế kiểm tra đăng nhập |
| Session hoặc danh tính bị đánh cắp | MFA, auth_version, revocation, hạn mức giao dịch/ngày, **tối đa 5 giao dịch hoàn tất trong 10 phút**, **lần đầu chuyển cho người nhận mới ≤ 10.000.000 VND** | Nếu cả session và kênh OTP bị chiếm, kẻ tấn công vẫn rút được tới các hạn mức này; không có bảo đảm tuyệt đối |
| Agent cố chuyển tiền qua staff | Staff không có `prepare_transfer`; staff tools ghi chỉ là `propose_*`, chờ người có quyền duyệt (role đọc lại từ DB lúc duyệt) | Admin vẫn có quyền quản trị riêng ở giao diện thủ công. Xem `RBAC_MATRIX.md` |

Outbox HTTP là mô phỏng local, chỉ bật khi `ENV=demo`. Nó không phải kênh xác minh độc lập an toàn như email thực. Ngoài demo, cả hai endpoint trả 404. Không dùng cấu hình này làm bằng chứng chống chiếm cả danh tính và OTP.

Giới hạn thiệt hại khi danh tính bị chiếm (đề xuất của nhóm, mentor đồng ý ngày 3/11) đã triển khai trong `backend/app/transfers.py`, kiểm tra cả lúc tạo draft và lúc xác nhận OTP (trong transaction lock): `VELOCITY_LIMIT_EXCEEDED` khi đã có 5 giao dịch hoàn tất trong 10 phút; `NEW_RECIPIENT_LIMIT_EXCEEDED` khi số tiền > 10.000.000 VND và chưa từng có giao dịch hoàn tất tới người nhận đó. Hạn mức mỗi giao dịch và theo ngày giữ nguyên. Test: `backend/tests/test_week7_limits.py`. Các giá trị là hằng số trong code, chưa cho admin chỉnh. Đây là giới hạn thiệt hại, không phải ngăn chặn: kẻ chiếm được cả session lẫn hộp thư OTP vẫn chuyển được một lần ≤ 10 triệu cho người nhận mới. `auth_version` là ràng buộc phiên/phiên bản danh tính, không phải chứng thực mật mã phần cứng của thiết bị.

## B5 — token xác nhận chuyển tiền có chữ ký (14/11/2026)

### Thiết kế

- **Phát token:** response của `POST /api/transfers`, `GET /api/transfers/{id}` và `POST /api/transfers/{id}/otp` có thêm `confirm_token` khi draft còn `PENDING_OTP`. Draft do agent đề xuất chỉ thành draft sau khi khách bấm duyệt; trang xác nhận tải draft và nhận token tại bước này. Mỗi lần tải là một token mới (`jti` mới). Token không được lưu vào DB (`backend/app/api/routes/transfers.py::with_token`).
- **Định dạng:** JWT HS256 ký bằng `TRANSFER_TOKEN_KEY` (khoá riêng, R8). `iss=novabank-demo`, `aud=transfer-confirm`, `sub=<transfer_id>`, `owner_id`, `to_bank`, `to_account`, `amount_vnd`, `iat`, `exp`, `jti` (`backend/app/transfer_token.py`).
- **Thời hạn:** `exp = min(iat + 300, hạn của draft)`. Expiry được so với đồng hồ của luồng chuyển tiền, là cùng đồng hồ quyết định draft hết hạn.
- **Kiểm tra ở `/confirm`** (bắt buộc, trong cùng transaction `BEGIN IMMEDIATE`): có token → chữ ký, `aud`, `iss` → `exp` → so khớp `sub` và từng trường với draft trong DB → (cache idempotency) → `jti` chưa dùng → trạng thái → OTP/PIN → hạn mức → ghi sổ, rồi ghi `jti` vào `transfer_token_uses` (khoá chính `jti`).
- **Một lần:** `jti` chỉ bị tiêu khi chuyển tiền thành công, nên nhập sai OTP/PIN vẫn thử lại được với cùng token (giới hạn 3 lần sai vẫn áp dụng). Gửi lại với cùng `Idempotency-Key` trả biên lai đã lưu, không tạo giao dịch thứ hai.
- **Khoá theo mục đích (R8):** `JWT_SECRET` (JWT đăng nhập và JWT ủy quyền agent), `QR_SIGNING_KEY`, `OTP_HASH_KEY` (digest OTP đăng nhập, action, chuyển tiền, đều là HMAC; R7), `TRANSFER_TOKEN_KEY`. Agent service không nhận khoá nào (`backend/.env.example`, `scripts/serve.py`).

### Trường hợp đã chặn

| Tấn công | Kết quả | Test (`backend/tests/test_transfer_token.py`) |
|---|---|---|
| Thiếu token | `403 TOKEN_REQUIRED` | `test_missing_token_is_refused` |
| Chữ ký hỏng, sai khoá, ký bằng khoá JWT đăng nhập, sai `aud`, chuỗi rác | `403 TOKEN_INVALID` | `test_bad_signature_or_audience_is_refused` (5 trường hợp) |
| Sửa `amount_vnd` hoặc `to_account` trong payload token | `403 TOKEN_INVALID` (chữ ký vỡ) | `test_amount_or_recipient_edited_inside_the_token_breaks_the_signature` |
| Token ký đúng nhưng cho số tiền, người nhận, ngân hàng hoặc chủ khác | `403 TOKEN_MISMATCH` | `test_token_for_other_parameters_is_refused_even_when_signed` (4 trường hợp) |
| Draft trong DB bị đổi sau khi phát token | `403 TOKEN_MISMATCH`, draft giữ nguyên `PENDING_OTP` | `test_draft_changed_after_the_token_was_issued_is_refused` |
| Token hết hạn | `403 TOKEN_EXPIRED` | `test_expired_token_is_refused` |
| Dùng lại token sau khi đã chuyển | `409 TOKEN_REPLAYED`; cùng `Idempotency-Key` vẫn trả biên lai cũ, chỉ một `jti` được ghi | `test_reused_token_is_refused` |
| Dùng token của user khác | `403 TOKEN_MISMATCH`; user khác chạm vào draft thì `404` | `test_another_users_token_is_refused` |

Các test còn lại kiểm tra luồng hợp lệ: token gắn đúng tham số và không bị lưu vào DB; sai OTP vẫn giữ token dùng được; tải lại draft cho token mới; sau khi hoàn tất không còn phát token. Luồng UI (duyệt → xác nhận → hoàn tất) chạy trong Playwright: `banking.spec.ts`, `week7.spec.ts`, `inbox.spec.ts`. Test khoá: `backend/tests/test_key_separation.py`.

### Khi danh tính bị đánh cắp

Token **không** giúp được gì nếu kẻ tấn công đã có phiên của khách: họ tải draft và nhận token như chủ tài khoản. Token chỉ ràng buộc lệnh xác nhận vào đúng tham số đã xem lại và làm cho nó dùng một lần. Nó chặn việc sửa số tiền hoặc người nhận giữa chừng (proxy kiểu Caido/Burp, XSS sửa request), chặn phát lại, và chặn agent (agent không có JWT của khách nên không lấy được token). Thứ còn bảo vệ khi danh tính bị chiếm:

1. **Step-up khi chuyển tiền:** PIN giao dịch hoặc TOTP, tách khỏi mật khẩu. Kẻ có mật khẩu đặt được PIN nếu khách chưa có PIN (xem chuỗi R1, `OUTBOX_TAKEOVER.md`).
2. **Hạn mức:** mỗi giao dịch ≤ 100.000.000 VND, theo ngày ≤ 200.000.000 VND, tối đa 5 giao dịch hoàn tất trong 10 phút, lần đầu chuyển cho người nhận mới ≤ 10.000.000 VND (`transfers.py`, `test_week7_limits.py`).
3. **Rate limit:** đăng nhập, gửi mã, tra người nhận, run agent, tra challenge của outbox.
4. **Thu hồi:** đổi mật khẩu, MFA hoặc trạng thái tài khoản sẽ tăng `auth_version` và huỷ mọi phiên.

Giới hạn: trong demo, MFA email không chặn được người đã có mật khẩu (`KNOWN_FAILURES.md`). Chưa có kênh xác nhận ngoài app.
