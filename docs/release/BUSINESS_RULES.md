# Business rules

1. Tiền là số nguyên VND. Chuyển tiền tối thiểu 1.000, cấu hình tối đa 100 triệu/lần và 200 triệu/ngày. Phí 0–100.000 VND được chốt khi tạo draft, xác nhận kiểm tra lại hạn mức và số dư gồm phí.
2. Một `BEGIN IMMEDIATE` giữ validation, ledger, balance cache, history, notification và audit. Tất cả journal cân bằng; lỗi giữa bước phải rollback. SQL write lock thay cho row-lock PostgreSQL trong stack SQLite này.
3. OTP transfer/product sống 120 giây, tối đa 5 lần sai, thuộc owner/session/purpose/payload. Agent không nhận OTP. Idempotency trả lại kết quả đã ghi cho cùng key; key khác không tái sử dụng code đã tiêu thụ.
4. Nội bộ hoàn tất đồng thời hai bên. Liên ngân hàng vào PENDING, worker xử lý sau ít nhất 5 giây. Account demo tận cùng `0000` bị từ chối có chủ đích để kiểm thử; reversal tạo journal mới trả cả gốc và phí. Không sửa journal cũ. Tài khoản frozen vẫn nhận compensating credit.
5. Không đóng tài khoản có số dư, settlement pending, tiết kiệm active hoặc dư nợ. Freeze ngăn debit; customer không tự sửa trạng thái tài khoản.
6. Debit mua hàng trừ tài khoản thanh toán; credit tăng dư nợ đến hạn mức 20 triệu. Repayment không lớn hơn dư nợ. Frozen card không cho purchase. Thanh toán hóa đơn recheck UNPAID dưới lock để tránh trả hai lần.
7. Tiết kiệm tối thiểu 100.000 VND; kỳ hạn 3/6/12 tháng lãi năm 4,5%/5%/6%. Đáo hạn: `floor(principal * rate_bps * months / 120000)`. Rút sớm lãi 0; tiền luôn về tài khoản nguồn. Lãi do SYS-INTEREST đối ứng, không tạo tiền ngoài journal.
8. Analytics chỉ lấy completed theo tháng. Cộng transfer fee; credit purchase ghi chi lúc mua. Loại principal gửi/rút tiết kiệm, credit repayment và refund transfer lỗi để tránh đếm lại. Sao kê vẫn hiển thị mọi trạng thái và phí, không suy đoán snapshot cho legacy history.
9. Profile đổi bằng current password + OTP. Email/phone gửi code đến địa chỉ mới qua local outbox. Đổi email hủy login challenge cũ và gửi notice đến email cũ. Đổi password tăng auth_version, thu hồi toàn bộ phiên.
10. Access JWT 5 phút, idle 5 phút, absolute session 8 giờ; refresh rotation single use. Có email MFA và TOTP với chống replay. Lockout 15 phút và quota lưu SQLite. Logout/revoke/disable có hiệu lực với cả delegated token.
11. Attachment tối đa 2 MiB/file, 5 file/ticket: PNG/JPEG/PDF/TXT; kiểm tra magic/UTF-8. Tải xuống attachment/octet-stream/nosniff/sandbox. Web render customer text dưới dạng text escaped.
12. QR riêng `NBQR1`, HMAC bảo vệ nội dung. Đọc original PNG có metadata hoặc paste payload. Không nhận screenshot/crop tùy ý, không dùng ứng dụng ngân hàng thật. JWT_SECRET ổn định giúp QR tồn tại qua restart.
13. Agent grant 180 giây, tối đa 8 tool/4 round/120 giây. Approval 600 giây, cùng session. Mọi write proposal gắn intent mới nhất, recipient/amount/bank độc lập với model. Hai tool bị từ chối trong defended dừng chuỗi. Admin có kill switch.

[Test plan](TEST_PLAN.md) nêu các ca xác nhận các invariant này. Giới hạn mô phỏng được hiển thị trong UI và [user guide](USER_GUIDE.md).
