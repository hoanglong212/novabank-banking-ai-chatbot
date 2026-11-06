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
| Session hoặc danh tính bị đánh cắp | MFA, auth_version, revocation, amount/daily limits | Nếu cả session và kênh OTP bị chiếm, không có bảo đảm tuyệt đối |
| Agent cố chuyển tiền staff | Staff tools chỉ đọc, no approval tools | Role admin ở giao diện thủ công vẫn có quyền quản trị riêng |

Outbox HTTP là mô phỏng local, chỉ bật khi `ENV=demo`. Nó không phải kênh xác minh độc lập an toàn như email thực. Ngoài demo, cả hai endpoint trả 404. Không dùng cấu hình này làm bằng chứng chống chiếm cả danh tính và OTP.

Cooldown người nhận mới là phần tùy chọn trong playbook, chưa triển khai. Hạn mức mỗi giao dịch và theo ngày hiện có vẫn giữ nguyên. `auth_version` là ràng buộc phiên/phiên bản danh tính, không phải chứng thực mật mã phần cứng của thiết bị.
