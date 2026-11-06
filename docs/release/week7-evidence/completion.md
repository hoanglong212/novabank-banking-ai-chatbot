# Week 7 — bàn giao và bằng chứng

**Local deployment đã hoạt động với Qwen 2.5 7B; chưa nghiệm thu toàn bộ playbook.** Theo dõi bộ đánh giá LLM trong [EVALUATION_STATUS.md](EVALUATION_STATUS.md); các lỗi quan sát và cách sửa nằm trong [KNOWN_FAILURES.md](KNOWN_FAILURES.md). Capture Caido/VM, profile/log demo ngày 3/11 và review độc lập còn thiếu.

**Cập nhật 06/11/2026:** Full Qwen đã kết thúc 2.070 lượt. Chạy lại 150 lượt tương ứng sau sửa làm số lỗi giảm từ 96 xuống 6; cả 90 lỗi trace tiết kiệm đã hết. Sáu lỗi giới hạn vòng xử lý/tham số model sai vẫn được ghi nhận, không nới guard để làm xanh kết quả. Xem [đối chiếu trước/sau](postfix-regression/comparison.md).

Mở http://127.0.0.1:8081. Alice: `alice / Alice@2026`; admin: `admin / Admin@2026`. Lấy mã đăng nhập trong http://127.0.0.1:8081/outbox. Đây là tài khoản và tiền mô phỏng. Cổng 8080 là phiên cũ. Hướng dẫn vận hành: [WEEK7_LOCAL.md](../WEEK7_LOCAL.md).

## Tiêu chí → bằng chứng

| Hạng mục | Kết quả và bằng chứng |
|---|---|
| WS0 baseline | `00-baseline.md`: 359 pytest, 17 nhóm component, 16 E2E; tag local `pre-week7`, branch `week7/integration` |
| WS1 bypass | `BYPASS_NOTE.md`, `backend/tests/test_PI_bypass_week7.py`: bổ sung nhận diện SYSTEM OVERRIDE; kiểm tra binding recipient độc lập. Chưa tái hiện lịch sử do thiếu profile/log |
| WS2 HTTP thật | Full Qwen 2.070 lượt và post-fix subset 150 lượt đã xong. Full run ghi nhận lỗi trước sửa; không trộn subset vào full run. Full mock giữ trong `mock-reference/` |
| WS3 RBAC | `RBAC_MATRIX.md`, `test_week7.py`, `role-checks.xml` (12 passed), `media/browser-check.json`, `media/admin-assistant.gif`: tool chỉ đọc, role do bank kiểm tra, Qwen đếm user thực tế |
| WS4 outbox | `test_week7.py`, E2E Week 7, `media/transfer-response.json`, `media/outbox-qr.gif`: API không trả demo_otp; inbox chỉ bật ENV=demo; chưa có capture Caido |
| WS5 link lab | `QUISHING.md`, `quishing-trace.json`, `quishing-ollama-trace.json`: model experimental fetch nhưng không đề xuất payment; probe scripted bị DENY. Không thay đổi QR app; dùng loopback thay VM |
| WS6 URL | `frontend/tests/e2e/week7.spec.ts`: review/OTP/receipt và approval tải trạng thái server; customer không mở staff page; API kiểm tra sở hữu |
| WS7 refactor | `create_app`, `api/routes`, package `agent` tương thích import cũ, request ID; backend/E2E đạt; cả hai lint đã cấu hình cũng đạt tại máy local |
| WS8 authz | `CRYPTO_AUTHZ.md`: flow token, binding, approval, OTP và giới hạn. Cooldown recipient mới là phần tùy chọn chưa làm |
| WS9 evidence | CSV, báo cáo, 7 slide HTML, video/GIF và response JSON. HTTP JSON thu bằng Playwright không được gọi là capture Caido |

## Kiểm tra thực tế

| Lệnh | Kết quả |
|---|---|
| `backend/.venv/Scripts/python.exe scripts/financial-coverage.py` | **388 passed**, 249.20 s, financial executed-line coverage **93.68%**; `.local/week7-verification-backend.log` |
| `npm run test:e2e` trong frontend | **20 passed**, 2.5 phút; `.local/week7-verification-e2e.log` |
| `npm run build` trong frontend | Đạt sau sửa gợi ý staff; `.local/week7-verification-build.log` |
| `npm run test:components` trong frontend | **17 nhóm đạt**; `.local/week7-verification-components.log` |
| `python -m compileall -q backend/app agent_service research scripts tools` | Đạt |
| `node scripts/check-week7-local.mjs` trong frontend | Port 8081: Alice/admin đăng nhập MFA; Qwen gọi balance, user count và savings; không page error |
| `node scripts/record-week7-ui.mjs` trong frontend | Ghi UI outbox/QR, kiểm tra response không OTP và URL QR bị 422; không confirm payment |
| `python -m research.quishing --provider ollama ...` | Hoàn tất cả defended/experimental; không approval hoặc transfer |
| `git diff --check` | Exit 0; cảnh báo chuyển LF/CRLF được lưu riêng |
| `python -m ruff check backend/app agent_service research scripts tools` | Ruff 0.14.3: exit 0, không lỗi với rules F821/F822/F823; `ruff-results.json` |
| `npm exec --yes --package=eslint@9.39.1 -- eslint --config eslint.config.mjs frontend/scripts` | ESLint 9.39.1: exit 0, không lỗi/cảnh báo với 5 correctness rules đã cấu hình cho scripts MJS; `eslint-results.json` |
| `python -m pytest backend/tests/test_week7_runner.py -q` | 7 passed sau bổ sung chọn subset theo ID; không chạy lại toàn backend vì thay đổi cuối chỉ ở runner/report, không sửa app |
| `scripts/start-week7-local.ps1` | Đã khởi động bank 8081/agent 8094, readiness đạt; thao tác dừng/restart phiên cũ chưa kiểm tra |

Ngày 06/11/2026, người dùng cho phép cài Ruff 0.14.3 vào venv và tải ESLint 9.39.1 vào cache npm; cả hai lint đã chạy và đạt. Đây là các correctness rules hiện được cấu hình, không phải toàn bộ recommended rules hoặc lint TypeScript; TypeScript được kiểm tra bởi lệnh build. Package manifest/lockfile không đổi. npm thông báo ESLint 9.39.1 không còn được hỗ trợ; vẫn giữ đúng phiên bản được duyệt và đang pin trong CI, chưa thực hiện nâng cấp phiên bản ngoài phạm vi này. `aef check` báo thiếu `engineering.json`; không khởi tạo framework mới. CI remote chưa chạy, không được tính là pass.

## Phạm vi thay đổi

- Backend: outbox và transfer OTP; staff tools/RBAC; approval GET; route extraction và agent import compatibility; request correlation; SPA fallback.
- Frontend: History API router; transfer/approval deep links; hộp thư; staff assistant và gợi ý phù hợp vai trò.
- Research/tooling: runner HTTP dùng DB riêng, kiểm tra link lab, báo cáo từ CSV, script khởi động local và ghi media.
- Sửa lỗi phát hiện qua kiểm tra thật: trace savings chấp nhận khóa số mà vẫn lọc secret; chọn New conversation không bị phản hồi lịch sử cũ ghi đè.
- Tests/CI/docs: route permission matrix, backend regressions, E2E, cấu hình lint correctness, tài liệu và evidence.

README có thay đổi của người dùng từ trước và được giữ nguyên. Không commit, push hoặc triển khai public.

## Review và giới hạn

Đã tự kiểm tra diff, quyền tool, outbox gating, sở hữu draft/approval và các báo cáo. **Chưa có reviewer độc lập**; không gán review của người triển khai thành review độc lập.

Legacy-off vẫn có gateway; baseline vẫn binding. Utility là proxy tool/argument, không chấm ý nghĩa toàn bộ câu trả lời. Canaries không có trong app và staff legacy được loại khỏi mẫu. Một source tool call không chứng minh payload đã đến model. Temperature 0 khiến các lần lặp không phải mẫu sinh ở nhiệt độ khác 0. Không suy rộng ASR 0 thành an toàn tuyệt đối.

Automatic approval review chặn lệnh dừng cây tiến trình để thử restart với `blocked by policy`; lý do chi tiết hơn không được cung cấp. Phiên local đang chạy được giữ nguyên, không thử lách chặn bằng cách khác.

Sau đó đã khởi động bản sửa trên cổng khác (8081/8094) bằng script được cung cấp, không dừng tiến trình nào. Readiness và ba luồng Qwen trên trình duyệt đều đạt. Bộ đo và tiến trình xuất evidence đã kết thúc; trạng thái cuối nằm trong `EVALUATION_STATUS.md`. Bảy slide đã được xem trực quan, gồm slide số liệu được cập nhật sau full run.

## Rollback

DB triển khai mới nằm tại `.local/week7-deploy/novabank-v2.sqlite3`, tạo bằng SQLite online backup từ DB demo riêng; DB đánh giá nằm tại `.local/week7-live/run-*`. Không ghi đè DB cũ. Trước khi đổi phiên bản, sao lưu DB local và giữ file khóa MFA đi kèm. Dừng bằng Ctrl+C ở terminal khởi chạy; phiên nền hiện tại cần người vận hành kiểm tra PID/command line trong `.local/week7-deploy/launcher-v2.pid` trước khi dừng.

So sánh các thay đổi với tag `pre-week7` rồi hoàn nguyên riêng phần Week 7 khi cần; không dùng reset toàn bộ vì có sửa đổi README của người dùng. Không tự xóa DB/evidence. Script khởi động lại: `scripts/start-week7-local.ps1`; backend/agent dùng cổng 8081/8094, Ollama riêng 11435.
