# Bước 0 — snapshot trước đợt bằng chứng Security/AI/Lab

Người dùng cho phép review, backup DB demo rồi commit **cục bộ trên nhánh hiện tại**;
không push. Nhánh: `feat/banking-core-foundation`.

Phạm vi review: inventory toàn bộ thay đổi chưa commit (264 file, khoảng 6.9 MB),
diff tracked và các ranh giới nhạy cảm trong file mới: migration/ledger, auth/session,
ownership, quota recipient, agent delegation/cancellation/output, data export,
backup, sandbox và cấu hình chạy/test. Đây là self-review, không phải review độc lập.

- Các thay đổi cộng dồn gồm banking core/ledger; identity/MFA/session; sản phẩm,
  analytics/support/admin; agent HTTP/RAG/approval/streaming; research harness;
  UI, local deployment, tài liệu và các sửa nghiệm thu ngày 01/11.
- `git diff --check` và compileall pass. Bộ kiểm tra trước snapshot đã ghi nhận
  271 pytest, 17 nhóm component và 15 E2E pass; không gọi kết quả đó là lượt chạy mới.
- Inventory commit không có DB, `.env`, khóa MFA/private key hoặc JWT thô. Archive
  research được kiểm tra JWT; dữ liệu nghiên cứu là synthetic, không chạy lại thí nghiệm.
- Backup dùng `scripts/backup.py`, SQLite backup API với **source mode=ro**, mã hóa
  Fernet, kèm MFA key. Key/archive/restore đều nằm trong `.local/security-ai-evidence`
  bị gitignore, không đưa vào commit. Restore vào đường dẫn mới, quick_check và
  reconcile bản khôi phục đạt; không chạy migration/reconcile trên DB demo nguồn.
- Không thay environment, restart server, reset DB hoặc push.

Điểm cần xử lý/kiểm chứng ở đợt sau snapshot:

1. Helper quota trong E2E nghiệm thu hardcode `backend/.venv/Scripts/python.exe`;
   CI dùng Ubuntu. Cần dùng cơ chế chọn Python sẵn có khi bổ sung E2E SEC-06.
2. Các điểm PII/trace và giới hạn tool/time cần bằng chứng bao trùm theo AI-07/10/15;
   không suy diễn đạt chỉ từ sự tồn tại của masking/budget trong code.
3. Dependency audit trước có advisory; phải quét mới SEC-10 và giữ trạng thái chưa
   đạt nếu còn lỗ hổng high/critical chưa xử lý. Không cài package trong đợt này.
4. Log thường bị gitignore; các báo cáo trong repo cần bằng chứng được chọn lọc và
   đã kiểm tra bí mật, không đưa toàn bộ log test chưa rà soát vào Git.

Commit này là mốc lưu các đợt đã làm, không phải xác nhận release/production safety.
Hash commit sẽ được ghi trong báo cáo của đợt 10 ca.
