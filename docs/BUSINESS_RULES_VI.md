# Business Rules v1 — phần core đã triển khai

Ngày 31/10/2026. Áp dụng cho demo local hiện tại, theo quyết định giữ stack. Đây là các rule có code/test, không phải tuyên bố đã hoàn thành M1–M2 trong PDF.

| Quy tắc | Hành vi hiện tại | Bằng chứng |
| --- | --- | --- |
| Tiền | Số nguyên VND; JSON float, chuỗi số, bool bị từ chối cho chuyển tiền | `test_transfer_requires_integer_vnd_in_range` |
| Số dư seed | Alice 12.500.000, Bob 8.750.000; startup không reset số dư đã thay đổi | `test_legacy_migration_uses_existing_balance_and_preserves_history` |
| Phí | 0 VND cho cả nội bộ và liên ngân hàng mô phỏng, giữ rule cũ | Posting có 2 dòng đối ứng; chưa có fee engine |
| Hạn mức | 1.000–100.000.000 VND/lần; 200.000.000 VND/ngày theo người gửi | Schema + kiểm tra lúc prepare và confirm |
| Ngày nghiệp vụ | Nửa đêm Việt Nam UTC+7; timestamp lưu UTC | `test_daily_limit_rechecked_at_confirm_using_vietnam_day` |
| Tài khoản | ACTIVE/FROZEN/CLOSED; chỉ ACTIVE gửi/nhận, không tự chuyển vào cùng tài khoản | `test_account_state_checked_during_prepare_and_confirm`, test cũ SAME_ACCOUNT |
| Ownership | Source thuộc user đăng nhập; transfer/OTP của người khác trả 404 | `test_cannot_debit_or_confirm_someone_elses_transfer` |
| Draft | PENDING_OTP, 5 phút kể từ prepare; hết hạn thì FAILED/DRAFT_EXPIRED | `test_expired_quote_cannot_be_revived_by_otp_resend` |
| OTP | Mọi chuyển tiền cần OTP; 6 số, 2 phút và không quá tuổi draft; tối đa 3 lần sai | Test OTP expiry/action binding/concurrent attempt budget |
| Resend | Đổi OTP, không reset số lần sai hoặc kéo dài tuổi draft | `issue_otp` giữ counter, TTL chặn bởi expires_at |
| Xác nhận | Lấy write lock trước đọc OTP/draft; kiểm tra lại state, balance, daily limit rồi ghi sổ | Tests concurrency, expired quote, frozen accounts |
| Idempotency | Key 1–128 ký tự `[A-Za-z0-9._:-]`, phạm vi `(user,key)`; cùng key + transfer đã thành công trả nguyên receipt cũ; khác transfer trả 409 | Tests replay, conflict, user scope, simultaneous confirm |
| OTP và retry | Lần nhập OTP sai không chiếm key. Cache receipt không lưu OTP/hash. Retry receipt vẫn cần JWT đúng chủ sở hữu | `test_wrong_otp_does_not_consume_idempotency_key` |
| Client cũ | Không có header key vẫn được nhận; confirm lặp trả ALREADY_PROCESSED, không ghi thêm tiền | Bộ test transfer gốc |
| Sổ cái | Debit âm, credit dương; mỗi journal ≥2 dòng, tổng = 0; balance cache khớp tổng ledger tài khoản | Shared reconciliation assertion; posting drift guard |
| Liên ngân hàng | Credit vào SYS-CLEARING, cập nhật COMPLETED ngay như demo cũ | `test_interbank_has_clearing_counterentry`; chưa có pending worker/reversal |
| Bất biến | Ledger, mapping ledger account, banking audit, receipt cache và báo cáo đối soát không UPDATE/DELETE/REPLACE. Transaction COMPLETED không bị sửa/xóa/replace | DB triggers + `test_posted_history_cannot_be_rewritten` |
| Rollback | Lỗi sau debit làm rollback balance, ledger, history, success audit, receipt; ghi FAILED riêng nếu storage cho phép | `test_rollback_after_debit_leaves_no_financial_effect` |
| AI | Chỉ tạo draft; OTP/confirm thuộc luồng UI; dispatcher không có tool confirm | Bộ test transfer/agent gốc và live smoke |

## Nâng cấp dữ liệu

`Database.initialize()` thêm migration version 1 trong transaction. Mỗi tài khoản được tạo ledger mapping và journal `OPENING:<account_id>` lấy **số dư tại thời điểm nâng cấp**, đối ứng `SYS-OPENING`. Nếu số dư bằng 0 thì chỉ tạo mapping. Số dư cũ, tin nhắn và lịch sử không bị reset. Startup sau không tạo lại opening để che mất sai lệch.

Lịch sử trước migration là lịch sử demo, không được dùng để kết luận có chứng cứ hạch toán quá khứ. Từ migration v3, xác minh email mở tài khoản mới 0 VND cùng ledger mapping trong một transaction; không tạo tiền hoặc journal opening có số tiền 0.

Sau khi khởi động backend mới, chạy từ root:

```powershell
.\backend\.venv\Scripts\python.exe scripts/reconcile.py --db backend/novabank_demo.sqlite3
```

Lệnh yêu cầu DB tồn tại, không khởi tạo/reset DB. Nó lưu một hàng `reconciliation_runs` và xuất JSON: exit **0** = cân, **1** = phát hiện lệch, **2** = đường dẫn/schema/quyền truy cập không hợp lệ. Đây là lệnh chạy thủ công, chưa phải job định kỳ.

## Các giới hạn chưa được thay thế

- Identity lưu SQLite, gồm 7 seed thuộc 5 vai trò và customer đăng ký mới. Login bắt buộc email/TOTP MFA, JWT 5 phút gắn session/credential version, refresh xoay vòng. Idle 5 phút, absolute 8 giờ; 5 lần sai trong 15 phút khóa 15 phút trong SQLite. Reset password thu hồi mọi phiên và challenge cũ; Security Center cho phép thu hồi từng phiên. [Quy tắc MFA/phiên](SESSIONS_MFA_VI.md), [register/verify/reset và dev outbox](ACCOUNT_RECOVERY_VI.md).
- OTP là SMS giả hiển thị trong ứng dụng; hash OTP hiện có không thay cho cơ chế OTP production. Chưa rate-limit resend/recipient lookup.
- Một write transaction tại một thời điểm với SQLite; chưa kiểm chứng tải cao hoặc nhiều server. Dùng `BEGIN IMMEDIATE` theo [tài liệu transaction của SQLite](https://www.sqlite.org/lang_transaction.html); không giả lập `SELECT FOR UPDATE` bằng câu SQL không được hỗ trợ.
- Chưa có phí cấu hình, SSE, danh bạ, journal reversal, banking worker. Đợt 01/11 đã bổ sung notification polling, PDF receipt, lịch sử có bộ lọc/phân trang và admin audit viewer.
- Nội dung chuyển khoản vẫn dùng chuẩn hóa/giới hạn 25 ký tự cũ; chưa phải bề mặt payload nguyên văn của Lab M5.
- Idempotency key ở UI sống trong một lần mở form; retry sau mất mạng giữ key, refresh trang thì mất key. Một draft vẫn không thể ghi tiền lần hai, nhưng chưa có màn khôi phục receipt theo draft.
- Chưa có bảo vệ khỏi quản trị viên có quyền sửa schema SQLite/drop trigger; các trigger bảo vệ đường ghi dữ liệu trong ứng dụng và thao tác SQL thông thường.
- VietQR hiện vẫn gọi nguồn ngoài để lấy danh sách/ảnh. Thay bằng QR mô phỏng là mục riêng còn thiếu so với PDF.

## Chi tiết, biên lai, thông báo và quyền đọc (01/11)

- Migration v2 tạo `transaction_details` bất biến. Mỗi giao dịch mới lưu số dư sau giao dịch và đối tác của từng bên, cùng transaction ghi tiền. Biên lai không dùng số dư hiện tại. Lịch sử cũ chỉ được backfill số dư nếu có success audit v1; phần còn lại hiện “Not recorded”.
- Chỉ giao dịch `COMPLETED` có PDF; khách không đọc/tải được giao dịch của người khác. PDF chứa dữ liệu giả lập, font tiếng Việt, reference, thời gian UTC+7, số tiền, đối tác, phí và số dư đã ghi nhận.
- Mỗi owner/transaction có tối đa một thông báo. Posting, chi tiết và thông báo cùng commit/rollback. Mark read và read-all luôn scope theo chủ sở hữu. Polling 15 giây chỉ hoạt động khi trang Alerts đang được hiển thị.
- Customer chỉ dùng API cá nhân. Operations/auditor/admin đọc được giao dịch toàn hệ thống và audit; support không có quyền này. Không có endpoint sửa số tiền hoặc ledger dành cho staff. Role trong JWT/browser không ghi đè role phía server.
- Ô tổng trên Home/Activity là **Completed activity** cho toàn bộ lịch sử đã có, loại `PENDING`/`FAILED`. Chưa triển khai thống kê theo tháng hoặc phân loại chi tiêu.
