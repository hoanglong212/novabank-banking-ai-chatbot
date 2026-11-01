# SEC-10 — nâng dependency và chốt code

Người dùng đã xác nhận phạm vi từ PDF (3): chỉ nâng bốn gói, cài pip-audit vào venv như công cụ dev, chạy audit và toàn bộ kiểm tra; commit cục bộ đợt Security / AI / Lab cùng bản nâng nếu tất cả đạt. Không push, không migrate/restart DB demo, không thực hiện M6 hay nghiên cứu model thật.

**SEC-10 đạt; cả 10 ca của đợt Security / AI / Lab đạt trong phạm vi test đã chọn.** Lượt cuối: 359 pytest, 17 nhóm component, 16 E2E đạt; coverage dòng tài chính 93,58%; reconcile cân bằng. Không nới hoặc bỏ test để làm xanh. Đây là kết quả trên code và DB test; backend demo đang chạy chưa được migrate/restart để áp dụng bản chốt.

| Gói | Trước | Sau đã cài | Advisory còn lại sau quét |
|---|---|---|---|
| certifi | 2026.7.22 | 2026.10.19 | 0 |
| pip | 26.1.2 | 26.2 (tương đương 26.2.0) | 0 |
| vite | 6.4.4 | 6.4.5 | 0 |
| postcss-selector-parser | 6.1.4 | 6.1.5 | 0 |
| pip-audit — công cụ dev mới | Chưa có | 2.10.1 | 0 |

`pip-audit --strict` quét đủ **110 package Python đã cài**, không package bị skip và không vulnerability. `npm audit --json` trả **0 vulnerability ở mọi mức**. Kết quả thô: [pip-audit.json](pip-audit.json), [npm-audit.json](npm-audit.json). Danh sách phiên bản thay đổi: [package-changes.json](package-changes.json).

## Cách thay đổi và kiểm soát phạm vi

- Dùng dry-run/report của pip cùng constraints khóa mọi package Python cũ ngoài certifi/pip. Sau cài, so lại toàn bộ inventory: chỉ đúng hai gói cũ này đổi phiên bản. pip-audit thêm 15 dependency cần cho công cụ; không nâng gói cũ khác.
- `backend/requirements.txt` thêm certifi với bản tối thiểu đã sửa; `requirements-dev.txt` ghi pip và pip-audit. Không đổi các dependency runtime còn lại.
- Vite pin 6.4.5; npm override chỉ áp dụng selector-parser `<6.1.5`, giữ nhánh 6.x. So toàn bộ lockfile: chỉ hai package Node đã chốt đổi phiên bản.
- Sau lần cài npm đầu, lockfile và hidden lock đã ghi bản mới nhưng manifest trong hai thư mục package còn bản cũ. Đã chuyển đúng hai thư mục cũ vào backup riêng trong `.local`, cài lại và xác minh trực tiếp `node_modules/*/package.json` cùng `require(...).version`. Không chỉ dựa vào `npm ls` hoặc audit lockfile.
- Quan sát `test_SEC_10.py` **fail trước khi nâng**. Sau đó chỉ cập nhật bằng chứng audit từ kết quả công cụ thật; không sửa test, không ignore advisory, không skip/xfail. Hai bản audit trước sửa được giữ tại [before-python.json](before-python.json), [before-npm.json](before-npm.json).
- Quét và kiểm thử chỉ sử dụng DB tạm; reconcile kiểm tra đường dẫn nằm trong `.local/e2e` trước khi chạy. Không thực hiện migration 9 hoặc restart demo.

## Lỗi fixture phát hiện trong lượt coverage

Lượt pytest thường đầu tiên đạt 359/359. Lượt coverage đầu tiên có 358 pass, 1 fail ở `test_TRF_14_ip_quota_survives_user_rotation_and_forwarded_header`: trả 400 thay cho kỳ vọng 429. Đọc DB tạm bằng `mode=ro` xác nhận 61 lần resolve bị chia giữa hai cửa sổ SQLite: 20 lần ở `1793542200`, 41 lần ở `1793542500`. Bộ đếm dùng cửa sổ cố định 300 giây; test trước đó phụ thuộc thời điểm thực nên có thể đi qua ranh giới trong lúc chạy.

Đã thêm fixture chỉ trong `backend/tests/test_TRF_14.py` để cố định `recipient_security.timestamp` trong từng test. Không thay assertion, quota, thời gian cửa sổ hoặc logic ứng dụng. Bốn test TRF-14 chạy riêng đạt sau sửa. Sau đó chạy lại toàn bộ chuỗi kiểm tra. Log và report của lượt thất bại được giữ riêng tại `.local/sec10-upgrade/attempt-1`; không bỏ qua thất bại bằng retry ngầm.

## Kiểm tra và bằng chứng

Lệnh thực tế cùng mã thoát và SHA-256 log được lưu tại [verification.json](verification.json); tất cả lệnh kết thúc với mã 0. Tổng hợp: [summary.json](summary.json). Bộ kiểm tra gồm:

1. `backend/.venv/Scripts/python.exe -m pip_audit --strict --progress-spinner off --format json --output ...`
2. `npm audit --json` từ `frontend`.
3. `backend/.venv/Scripts/python.exe -m pip check` và `-m compileall -q backend/app agent_service research scripts`.
4. `.venv/Scripts/python.exe -m pytest -q --tb=short` từ `backend`.
5. `backend/.venv/Scripts/python.exe scripts/financial-coverage.py` — chạy lại toàn pytest theo gate coverage tài chính hiện có.
6. `npm run test:components` và `npm run test:e2e` từ `frontend` — E2E gồm TypeScript/Vite build.
7. `backend/.venv/Scripts/python.exe scripts/reconcile.py --db <DB E2E mới>`.
8. Quét log thô sau toàn suite, không sanitization trước khi đánh giá.

| Kiểm tra | Kết quả lượt cuối | Bằng chứng |
|---|---|---|
| SEC-10 trước nâng | 1 fail đúng advisory/thiếu scanner | [SEC-10-before.txt](SEC-10-before.txt) |
| Pytest đầy đủ | 359 pass, 0 fail | [pytest-output.txt](pytest-output.txt) |
| Gate coverage tài chính | 359 pass; 93,58% dòng thực thi, ngưỡng 80%; không phải branch coverage | [financial-coverage.json](financial-coverage.json) |
| Component | 17 nhóm pass | [component-output.txt](component-output.txt) |
| TypeScript/Vite build và E2E | 16 pass | [e2e-summary.txt](e2e-summary.txt) |
| Reconcile DB E2E riêng | balanced=true; ledger_total_vnd=0; không mismatch/unbalanced journal | [reconcile.json](reconcile.json) |
| pip check / compileall | Đạt | [verification.json](verification.json) |
| Quét log thô | 0 mẫu bí mật được phát hiện theo bộ pattern đã ghi | [verification.json](verification.json) |

Các ca SEC-04/06/09, AI-05/07/10/15, PI-02/04 cùng test/file và bằng chứng đỏ→xanh được ghi trong [bảng đợt Security / AI / Lab](../security-ai-evidence/REPORT_VI.md). Bản báo cáo đó giữ trạng thái lịch sử trước nâng dependency; SEC-10 hiện đã được khắc phục bằng bản nâng này.

## Mốc Git

Nhánh hiện tại: `feat/banking-core-foundation`. Commit Bước 0 trước đợt Security / AI / Lab: `baf4eddb96f01f03a0c54d70e25e25f32210dd15`. Commit chứa báo cáo này chốt các sửa Security / AI / Lab, dependency và fixture TRF-14; hash mới được trả trong thông báo bàn giao sau khi tạo commit. Không push. DB, backup, khóa riêng và log thô nằm ngoài Git.

Review: Codex self-review, chưa có review độc lập. Các lệnh chạy trên Windows; CI Ubuntu chưa chạy vì phạm vi không push. Các kết quả cũ trong `security-ai-evidence` là lịch sử đợt trước; bằng chứng SEC-10 tại đây là đợt nâng đã được người dùng cho phép.

Không diễn giải audit sạch là không tồn tại mọi lỗ hổng: kết quả phản ánh các advisory mà dịch vụ quét biết ở thời điểm chạy. Rollback nếu cần phải áp dụng patch chọn lọc và cài lại phiên bản đã duyệt; không rollback đè DB demo, không dùng reset toàn workspace. Các thư mục package cũ được giữ trong `.local/sec10-upgrade/before`.
