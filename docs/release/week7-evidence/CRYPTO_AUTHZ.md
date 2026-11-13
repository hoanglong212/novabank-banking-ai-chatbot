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
Bank confirmation + OTP + idempotency → atomic ledger posting
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
| Agent cố chuyển tiền staff | Staff tools chỉ đọc, no approval tools | Role admin ở giao diện thủ công vẫn có quyền quản trị riêng |

Outbox HTTP là mô phỏng local, chỉ bật khi `ENV=demo`. Nó không phải kênh xác minh độc lập an toàn như email thực. Ngoài demo, cả hai endpoint trả 404. Không dùng cấu hình này làm bằng chứng chống chiếm cả danh tính và OTP.

Giới hạn thiệt hại khi danh tính bị chiếm (đề xuất của nhóm, mentor đồng ý ngày 3/11) đã triển khai trong `backend/app/transfers.py`, kiểm tra cả lúc tạo draft và lúc xác nhận OTP (trong transaction lock): `VELOCITY_LIMIT_EXCEEDED` khi đã có 5 giao dịch hoàn tất trong 10 phút; `NEW_RECIPIENT_LIMIT_EXCEEDED` khi số tiền > 10.000.000 VND và chưa từng có giao dịch hoàn tất tới người nhận đó. Hạn mức mỗi giao dịch và theo ngày giữ nguyên. Test: `backend/tests/test_week7_limits.py`. Các giá trị là hằng số trong code, chưa cho admin chỉnh. Đây là giới hạn thiệt hại, không phải ngăn chặn: kẻ chiếm được cả session lẫn hộp thư OTP vẫn chuyển được một lần ≤ 10 triệu cho người nhận mới. `auth_version` là ràng buộc phiên/phiên bản danh tính, không phải chứng thực mật mã phần cứng của thiết bị.
