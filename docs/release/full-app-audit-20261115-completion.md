# Kiểm tra chức năng toàn ứng dụng — 15/11/2026

Phạm vi: đối chiếu 25 use case trong SRS với regression backend, component, trình duyệt, model thật và kiểm tra tính nhất quán dữ liệu. Đây là kiểm tra chức năng trên môi trường local; không phải chứng nhận ứng dụng không còn lỗi. Các test dùng DB riêng. Dữ liệu localhost chỉ được kiểm tra bằng kết nối SQLite read-only.

## Kết quả lệnh

| Kiểm tra | Kết quả |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short` | 685 passed, 1 xfailed, 1 warning; 280.87 giây. Chạy trước khi thêm ca audit múi giờ bên dưới. |
| `cd frontend; npm.cmd run test:components` | 19 nhóm đạt |
| `cd frontend; npm.cmd run test:e2e` | Build đạt; kết quả 41 ca trình duyệt sẽ cập nhật khi hoàn tất |
| `backend/.venv/Scripts/python.exe scripts/check-agent-service.py` với `OLLAMA_URL=http://127.0.0.1:11435` | Đạt: balance, policy/RAG, transfer proposal, cancellation; tiền không thay đổi; model Qwen 2.5 7B thật |
| `backend/.venv/Scripts/python.exe scripts/check-migrations.py` | Đạt trên bản sao hai DB; nguồn không thay đổi; integrity và ledger đạt |
| `backend/.venv/Scripts/python.exe -m ruff check backend/app agent_service scripts backend/tests --output-format concise` | Đạt tại thời điểm chạy |
| ESLint | Chưa chạy được: không có executable ESLint trong dependencies frontend hiện tại; không cài thêm |
| SQLite localhost read-only | integrity=ok, ledger total=0, 0 lệch số dư, 0 journal mất cân bằng, 0 lỗi foreign key |

Log nằm tại `.local/full-app-audit-20261115/`. `real-agent-report.json` chứa trace model thật; `migration-report.json` chứa kiểm tra migration; `live-database.json` chứa kiểm tra DB hiện hành.

## Lỗi mới đã tái hiện

### A01 — Chi tiêu thẻ tín dụng vào sai tháng/ngày (mức vừa)

- Vị trí: `backend/app/insights.py:57` và `:59`.
- SQL lấy 10 ký tự đầu `created_at` UTC để phân tháng, trong khi giao dịch ngân hàng và UI dùng ngày Việt Nam.
- Tái hiện: mua thẻ tín dụng 100.000 VND tại `2030-10-31T17:30:00+00:00`, tương ứng 00:30 ngày 01/11 ở Việt Nam. API insights tháng 11 trả expense=0, kỳ vọng 100.000.
- Regression: `backend/tests/test_audit_credit_timezone.py`; lệnh riêng trả 1 failed do `0 != 100000`, không phải lỗi thiết lập fixture. Clock được cố định riêng ở bước posting; không sửa dữ liệu đã ghi, không vô hiệu trigger immutable.
- Ảnh hưởng: tổng chi tiêu, biểu đồ ngày và đánh giá ngân sách thẻ tại ranh giới tháng lệch với giờ Việt Nam. Chưa chứng minh mất tiền hoặc lệch sổ cái.
- Hướng sửa: dùng cùng ngày nghiệp vụ Việt Nam và khoảng thời gian UTC tương ứng khi đọc lịch sử thẻ.

### Các ca dashboard bổ sung

Đã thêm `frontend/tests/e2e/audit-consistency.spec.ts` để kiểm chứng: thống kê tháng cập nhật sau chuyển tiền tại Home; lỗi `/api/me` có thông báo/thử lại; lỗi insights có thông báo thay vì skeleton vô thời hạn. Chưa kết luận cho tới khi ca chạy xong.

## Ma trận chức năng và bằng chứng

| UC | Chức năng | Nguồn regression chính |
|---|---|---|
| 01 | Đăng ký, xác minh, đăng nhập, MFA, khôi phục, phiên | `test_identity.py`, `test_sessions_mfa.py`, browser identity/security |
| 02 | Dashboard và số dư | `test_balance_consistency.py`, browser acceptance-fixes; audit bổ sung |
| 03 | Hồ sơ và security center | `test_customer_products.py`, `test_profile_server_owned.py`, browser security |
| 04 | Tài khoản và ownership | `test_banking_core.py`, `test_customer_products.py` |
| 05 | Chuyển tiền, phí, hạn mức, idempotency | `test_transfers.py`, `test_transfer_token.py`, `test_week7_limits.py`, browser banking/week7 |
| 06 | Lịch sử, tìm kiếm, chi tiết | `test_services.py`, browser banking |
| 07 | Người nhận | `test_BEN_01.py`, browser acceptance-fixes/products |
| 08 | Ledger và atomic posting | `test_ledger.py`, `test_product_invariants.py`, kiểm tra DB read-only |
| 09 | Thông báo, tùy chọn, hộp thư demo | `test_notification_preferences.py`, `test_notification_tabs.py`, browser inbox/products |
| 10 | Biên lai PDF | `test_services.py`, browser banking |
| 11 | Thẻ, khóa/mở, mua hàng, trả nợ | `test_product_invariants.py`, browser explore-services/products; A01 chưa đạt |
| 12 | Hóa đơn, thanh toán một lần | `test_customer_products.py`, `test_product_invariants.py`, browser products |
| 13 | QR nhận/đọc, camera, OCR | `test_qr_browser_policy.py`, `test_guard_qr_langgraph.py`, browser qr-pay |
| 14 | Tiết kiệm, mục tiêu, calculator | `test_product_invariants.py`, browser explore-services/products, component calculator |
| 15 | Phân tích, phân loại, ngân sách | `test_PFM_02.py`, `test_release_boundaries.py`, browser explore-services; A01 chưa đạt |
| 16 | Sao kê PDF/CSV | `test_STM_01.py`, browser products/explore-services |
| 17 | Ticket, trả lời, đính kèm, staff | `test_support_rbac.py`, browser products/z-security-ai |
| 18 | Admin, quyền, cài đặt, reconciliation | `test_admin_dashboard.py`, `test_ADM_02.py`, `test_ADM_03.py`, browser admin-dashboard |
| 19 | Assistant, SSE, dừng, lịch sử | `test_chat.py`, `test_AI_12.py`, browser acceptance-fixes/week7, model thật |
| 20 | Tool, DTO, ownership, intent, quota | `test_agent_boundary.py`, `test_week7_intent.py`, `test_AI_07.py` |
| 21 | Knowledge/RAG | `test_AI_11.py`, `test_release_boundaries.py`, model thật |
| 22 | Proposal và approval | `test_rbac_proposals.py`, `test_admin_agent.py`, browser week7, model thật |
| 23 | Research sandbox | `test_research_invariants.py`, `test_week7_runner.py` |
| 24 | Trace, token, privacy | `test_agent_gateway.py`, `test_gateway_audit.py`, `test_key_separation.py` |
| 25 | Dashboard research và export | `test_gateway_session.py`, `test_week7_capture.py`; chưa chạy lại chiến dịch model/adversarial toàn bộ |

## Phạm vi rà soát và giới hạn

Đọc mã tập trung vào nhất quán dashboard/agent: `frontend/src/App.tsx`, `components/home/Home.tsx`, `components/home/Rail.tsx`, `components/explore/useProducts.ts`, luồng balance và output filter, truy vấn insights. Không tuyên bố đã review thủ công từng dòng toàn bộ repository. Kiểm tra injection/XSS, authentication, authorization/IDOR, session/replay, concurrency, cryptography và disclosure dựa trên regression hiện có; không coi test xanh là bằng chứng không có lỗ hổng. Không chạy pentest thích ứng, load test, CI remote hoặc triển khai Docker/VPS.

Không có engineering.json. Không cài dependency. Không chạy lại stdlib trace financial coverage vì đã chạy toàn bộ backend và mục tiêu là kiểm tra hành vi, không đo coverage. Không có ESLint executable; không xem mục này là đạt. Browser test hiện có phần agent dùng mock/legacy; kiểm tra model thật riêng chỉ bao gồm các ca nêu trên. Nguồn ảnh màn hình lấy từ Playwright; kiểm tra desktop/mobile theo các viewport của suite.

Rà soát do chính agent thực hiện, chưa có reviewer độc lập. Thay đổi của đợt audit chỉ thêm test tái hiện và báo cáo; không thay đổi production code. Các sửa số dư từ đợt trước được giữ nguyên. Các test audit đỏ được giữ lại để có thể xác minh bản sửa sau này. Rollback đợt audit: bỏ các file test mới và báo cáo này; không cần đổi database hay cấu hình.
