# Trạng thái bàn giao — 01/11/2026

**Đợt sửa nghiệm thu sau audit đã kiểm chứng 10 ca được yêu cầu và 4 quyết định đặc tả.** Kết quả cuối: 271 pytest, 17 nhóm component, 15 E2E pass; reconcile cân bằng; financial line coverage 93,58%. Xem [bảng trước/sau, lệnh và log](acceptance-fixes/REPORT_VI.md). AI-14 / PI-05 / PI-06 hoãn theo yêu cầu. Server demo hiện có chưa được restart; backend đang chạy cần restart để nhận code mới.

[Audit 121 ca ban đầu](acceptance-audit/REPORT_VI.md) được giữ nguyên làm bằng chứng lịch sử. Không suy diễn toàn bộ các tiêu chí nghiên cứu đã hoàn tất từ kết quả đợt sửa này.

Người dùng chốt “local thôi”. VPS, tên miền, HTTPS công khai và phát hành remote nằm ngoài phạm vi hiện tại. Không tuyên bố đã phát hành v1.0 hoặc đạt chứng nhận an toàn production.

**Đã khởi chạy local theo yêu cầu:** http://127.0.0.1:8080, agent :8093, database demo riêng. Xem [đăng nhập, MFA và khởi động lại](LOCAL_RUN.md).

## Mốc thực hiện

| Mốc | Kết quả |
|---|---|
| M1 | Authentication/MFA/session, profile và đổi password/contact có OTP |
| M2 | Ledger, transfer/fee/limits, interbank pending/reversal, QR nội bộ, receipts/alerts/reconcile worker |
| M3 | Cards, bills, savings/goals/calculators, analytics/budgets/statements, support/admin/knowledge |
| M4 | Agent HTTP riêng, delegated token, RAG nomic có nguồn, approvals, SSE progress, trace |
| M5 | Sandbox reset, 35 scenarios/7 vectors, 100 legitimate tasks, 3 profiles, 2 models, 5 repeats và ablation |
| M6 local | Header/CORS/body limits, scans, CI/Compose/Caddy config, encrypted backup/restore, seed, docs, slides HTML và video |
| M6 phát hành ngoài máy | Ngoài phạm vi theo quyết định chỉ chạy local; cấu hình được giữ để tham khảo nếu mở rộng sau này |

UI tiếp tục tiếng Anh theo quyết định dự án đã chốt, không tự đổi sang bản song ngữ. Profile có notification preferences cho nhắc hóa đơn và ngân sách; security/money alerts luôn bật. P2 (khoản vay thật, thẻ ảo, chuyển định kỳ/hàng loạt, live chat, dark mode) không được thêm. KYC, email/SMS và mọi tiền đều mô phỏng. Vì vậy không coi “25 use cases có triển khai” là mọi dòng trong PDF đều đã xong.

## Kiểm tra đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Backend + financial coverage | **224 passed**, 93,27% executed-line coverage ở 5 module tài chính |
| Frontend components | **15 nhóm đạt**, gồm session coordination và lịch trả nợ |
| Build | TypeScript + Vite đạt, JS ~382 kB (~110 kB gzip) |
| Playwright regression | **12 passed**, gồm Alice–Bob, MFA/recovery/session, products/support/mobile |
| Agent thật | Qwen HTTP service tách riêng + 8 document/chunk nomic; balance/policy/proposal đạt |
| UI release | **44 snapshots** ở 375/768/1440; không tràn ngang, thiếu nhãn hay pageerror; real SSE + approval đạt |
| Research | **1.790/1.790**, 0 lỗi chạy, ledger cân; defended utility Qwen99%/Llama90%, ASR0 trong corpus |
| Migration | Legacy backend DB v2 → v8 trên bản sao, old rows/integrity/ledger đạt. Root DB gốc rỗng được khởi tạo trên bản sao |
| Bảo toàn nguồn | SHA256 của cả hai file DB gốc không đổi |
| Restore | 52 bảng giống snapshot; MFA key khôi phục; từ chối overwrite target |
| Compose / source | `docker compose config --quiet`, Python compileall và `git diff --check` đạt |
| Dependency scan | npm: 2 moderate, 0 high/critical; OSV: advisories ở certifi/pip trong 94 distributions |

Phát hiện từ xem video: model từng nói proposal đã approved và gợi ý OTP trong chat. Đã thêm regression đỏ/xanh, đổi finish boundary để dùng thông báo trạng thái nhạy cảm do Banking API tạo, kiểm tra browser và quay lại video. Raw thí nghiệm lab giữ nguyên vì đây là workflow ứng dụng, không thay dataset/engine đo đã đóng băng.

## Bằng chứng và sản phẩm bàn giao

[Coverage](evidence/financial-coverage.json), [migration](evidence/migration.json), [restore](evidence/restore.json), [agent service](evidence/agent-service.json), [UI report](evidence/ui-report.json), [research](PI_RESULTS.md), [security PDF](Security-Evaluation.pdf), [video demo](media/NovaBank-demo.mp4), [slide HTML](Defense-Slides.html).

[Tổng hợp xác minh cuối](evidence/verification.json), [log backend](evidence/backend-tests.log), [log component](evidence/component-tests.log), [log build/E2E](evidence/browser-build-tests.log). Lượt 44 ảnh UI chạy trước khi thêm notification preferences; lượt E2E cuối đã kiểm tra cài đặt này và việc lưu lại sau reload. Các tiến trình phục vụ QA ở cổng 8084/8094 đã dừng sau khi kiểm tra.

Video là ghi hình thao tác thật với phụ đề, không có thuyết minh âm thanh. Slides là bản HTML offline, dùng phím mũi tên để trình chiếu; chưa xuất PPTX vì runtime presentation tích hợp không khả dụng. Không có dữ liệu DB/outbox/key trong bundle tài liệu.

## Phạm vi local đã chốt và giới hạn còn lại

1. Chạy trực tiếp trên máy bằng launcher trong [hướng dẫn local](DEPLOYMENT.md). Không cần VPS/domain/ACME hoặc Docker để nghiệm thu phạm vi này. Cấu hình container/HTTPS chưa được chạy thực tế và chỉ là phương án triển khai thêm.
2. Không yêu cầu push, CI remote, commit/tag/release trong phạm vi local. Các kiểm tra local đã chạy có bằng chứng phía trên; chưa có GitHub Actions run cho diff hiện tại. Thay đổi cũ chưa commit được bảo toàn.
3. Dependency advisories vẫn còn như kết quả scan; việc chỉ chạy local không xóa các cảnh báo này. Chưa cập nhật gói vì AGENTS yêu cầu không auto-install dependencies/services.
4. Giữ quyết định stack/UI đã chốt; vi/en và P2 vẫn ngoài phạm vi. Đây là hoàn thành bản local theo phạm vi đã điều chỉnh, không phải khẳng định mọi mục phát hành trong PDF gốc đã thực hiện.

Không có review độc lập, pentest, load test nhiều máy hoặc bảo chứng production security. Những hạn chế này được giữ trong báo cáo và slides.
