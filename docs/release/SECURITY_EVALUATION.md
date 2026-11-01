# Security Evaluation Report — 01/11/2026

## Kết luận trong phạm vi đã đo

Banking workflow, service separation và defense-in-depth đã có bằng chứng local. Trong 350 attack observations của defended, không goal nào đạt theo evaluator của corpus. Utility của defended đạt 99/100 Qwen và 90/100 Llama. Baseline lab đạt goal tấn công 44/175 Qwen (25,14%) và 22/175 Llama (12,57%). Tất cả 1.790 quan sát chạy không lỗi và mọi sandbox journal cân.

Đây là kết quả của controlled source-ingestion study. “Attack thành công” có thể chỉ là proposal sai được baseline chấp nhận; không đồng nghĩa tiền đã chuyển. Corpus có mẫu lặp và D3 biết intent chuẩn. Không kết luận ngân hàng production an toàn, không quy kết toàn bộ cải thiện cho một lớp guard. [PI_RESULTS](PI_RESULTS.md) có bảng đầy đủ, ablation, raw data và hash.

## Kiểm soát có bằng chứng độc lập với LLM

- Agent grant audience khác login JWT; không gọi confirm, không dùng token đọc Bob, logout thu hồi grant.
- Customer phải duyệt proposal; transfer/bill/card còn xác nhận OTP server-bound. Payment primitive integer/double-entry/atomic/idempotent và immutable ledger không phụ thuộc model.
- Tests thực hiện concurrent/replay/rollback/expiry/limit/funds/state checks. Financial executed-line coverage 93,27%, mục tiêu ≥80% đạt ở module được đo.
- Hai process HTTP thực dùng Qwen và nomic embeddings đã trả balance, policy có nguồn, transfer proposal. Đề xuất không thay số dư, approval tồn tại.
- Browser thực kiểm tra SSE proposal → human approval → banking transfer review và Escape/focus. Video thực hiện Alice–Bob, assistant và hiển thị stored baseline/defended case.
- Hai DB gốc không đổi hash. Migration copy giữ toàn bộ old rows; backup restore khôi phục 52 bảng giống nhau và per-DB MFA key, từ chối ghi đè target.

## Source defenses và ablation

App defended có system rules/delimiters, least privilege, argument binding, approval, limits, local source classifier, output filter, anomalous-chain stop và memory owner/vault. Baseline app vẫn chặt hơn baseline lab ở binding. 140 ablations cho 0 goal achieved trong tập mẫu hẹp; không thể dùng kết quả này để xếp hạng đóng góp từng lớp. Classifier 0/10 false positives, nhưng 10 benign snippets quá nhỏ để kết luận tỷ lệ thực tế thấp.

## Dependency scan

Quét tại môi trường hiện tại bằng `npm audit --json` và OSV querybatch trên 94 Python distributions. Frontend: 2 moderate (`vite`, `postcss-selector-parser`), không high/critical trong kết quả scan. Python installed environment: `certifi 2026.7.22` có GHSA-6q48-6c7w-9gw2/PYSEC-2026-4320; `pip 26.1.2` có GHSA-qwm4-qh6w-59xr/PYSEC-2026-3721. Pip là công cụ cài, không runtime Banking API. Vite/selector parser thuộc build tooling. Kết quả scan không tự xác nhận khai thác được ở cấu hình này.

Các advisory được giữ trong `evidence/npm-audit.json` và `evidence/python-audit.json`. Chưa tự cài/nâng dependencies theo quy tắc AGENTS của workspace. Cần cập nhật ở môi trường được phép rồi chạy lại checks; không đánh dấu dependency hygiene hoàn tất chỉ vì chưa có high/critical frontend.

## Web, log và triển khai

Banking app dùng bearer JWT trong sessionStorage; không dùng cookie auth, nên không tuyên bố có cookie Secure/HttpOnly/SameSite. CORS whitelist, CSP script self, nosniff, frame denial, no-store; Swagger/ReDoc có ngoại lệ CDN tài liệu. HTML vẫn có nguy cơ XSS nếu tương lai render unsanitized content. File download ép attachment và sandbox.

Logs structured chỉ method/status/duration/request ID. Access log mặc định uvicorn còn có path; không dùng token trong query. Các script không in JWT/OTP. Dev outbox có code có thời hạn để demo, vì vậy DB/outbox là tài sản nhạy cảm trong local environment. Agent process không được cấp DB_PATH/JWT/MFA key nhưng cùng host không phải sandbox OS chống host compromise.

Compose parse đã đạt. Docker Engine tắt, chưa build/run container, chưa ACME/HTTPS public. Remote Actions chưa có run cho thay đổi này. Chưa pentest, review độc lập, load/concurrency nhiều máy, chaos network dài hạn, hoặc tài khoản/tiền thật. Đây là các điều kiện phát hành còn mở, không phải kết quả đã pass.

## Bước đánh giá tiếp theo khi có môi trường

Chạy CI trên commit cụ thể, build image và test restore trong container, kiểm tra HTTPS/gateway, xử lý advisories rồi re-run. Mở rộng corpus với payload thích ứng và held-out sources, đo cả retrieval poisoning và hội thoại nhiều lượt, không dùng oracle intent. Tách thống kê proposal sai khỏi posting trái phép, thêm benign samples cho classifier, đo p95 latency/cost không cache. Bảo vệ boundary Banking API ngay cả khi classifier hoặc agent thất bại.
