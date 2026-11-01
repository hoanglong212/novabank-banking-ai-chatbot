# Kết quả kiểm thử theo kế hoạch mới — 01/11/2026

**Chưa có đầy đủ mọi tính năng/hành vi trong PDF mới.** Bản local có các luồng ngân hàng chính hoạt động và bộ test cũ đạt, nhưng vẫn còn khoảng thiếu về danh bạ, sao kê, dashboard, cảnh báo ngân sách, quyền staff và AI. Kết luận “hoàn tất local” trước đây dựa trên phạm vi triển khai cũ; không đủ để xác nhận đã đạt 121 ca của PDF kiểm thử vừa cung cấp.

Nguồn đối chiếu: PDF “Kế hoạch kiểm thử NovaBank (Banking Web App + AI Agent)”, 21 trang. Đã đọc toàn văn và đối chiếu trực quan bảng quyền trang 12. Đoạn “Giao cho trợ lý code” trong PDF được xem là nội dung tài liệu, không tự động thực hiện đổi tên test hoặc sửa logic sản phẩm. Người dùng yêu cầu kiểm thử mức đầy đủ; audit này chỉ thêm probe, bằng chứng và báo cáo. Local-only vẫn là phạm vi triển khai; không yêu cầu VPS/HTTPS/CI remote để dùng local.

## Kết quả thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Bộ backend hiện có | 224 passed, 90,96 giây; financial line coverage 93,27% ở 5 module, không phải coverage toàn ứng dụng |
| Component / build / E2E | 15 nhóm component; TypeScript/Vite build đạt; 12 E2E passed trong 1,2 phút |
| Probe mới đối chiếu PDF | 23 assertions/cases: 9 passed, 14 failed; các fail gồm thiếu tính năng và khác hợp đồng/chính sách, không đồng nghĩa 14 lỗi bảo mật |
| Tải nhẹ NF-01 | 20 tài khoản/20 VU, 120,65 giây, 3.300/3.300 transfers; 0 lỗi/locked; p95 cả draft+confirm 989,44 ms; ledger cân |
| Backup/restore NF-03 | Lấy snapshot khi đang tải, mã hóa, restore DB mới; reconcile, MFA login và đọc account đều đạt |
| Restart NF-04 | Process khởi động lại với draft còn hạn; OTP cũ 200, replay cùng key chỉ trừ tiền một lần |
| UI bổ sung | 15 captures ở390/768/1280; keyboard transfer, retry mất response và HTML nickname đạt; phát hiện show-balance preference và cancel chat thiếu |
| Agent thật | Qwen qua 2 HTTP process: balance đúng12.500.000, savings policy5%, transfer proposal không di chuyển tiền; 8 document/chunk nomic |

Các test ghi tiền chỉ dùng DB tạm/DB audit riêng. Không gửi lệnh tài chính vào bản local8080 của người dùng. Hai DB gốc có SHA256 giữ nguyên. Không cài thêm dependency, không commit/push. Metadata source tree và commit gốc nằm trong [summary.json](summary.json); working tree có thay đổi chưa commit từ trước.

## Điểm chưa đạt cần xử lý

| Mức / mã | Bước tái hiện và thực tế | Phần còn thiếu |
|---|---|---|
| Trung bình — BEN-01 | Lưu hai recipient, tìm Family vẫn trả cả hai; PATCH nickname trả405. UI chỉ có Transfer/Remove/Add. | Sửa nickname, tìm kiếm danh bạ và tests owner/persistence. |
| Cao theo tiêu chí rate-limit của PDF — TRF-14 | 40 request POST /api/transfers resolve Bob đều 201, trả tên; chưa confirm nên không trừ tiền. | Rate limit việc dò recipient qua đường tạo draft; quota lưu beneficiary hiện có không bao phủ đường này. |
| Trung bình — PFM-02 | Đặt budget1000, chuyển2000: 0 BUDGET alert. Mở insights mới có1 alert. | Đánh giá ngưỡng khi posting hoặc worker, dedupe không phụ thuộc việc mở trang. |
| Trung bình — STM-01 | Tải CSV/PDF theo kỳ hiện chỉ có từng giao dịch và balance-after. | Opening/closing balance, tổng credit/debit theo kỳ và đối soát với ledger. CSV formula escape đã có. |
| Trung bình — SEC-01 | Operations không khóa account được403; auditor không đọc ticket khách404; operations/auditor đọc research200, operations list ticket200, support đọc alerts200. | Thống nhất ma trận quyền với PDF. Read-only alerts của staff có thể là lựa chọn hợp lý, không tự kết luận là lộ dữ liệu. Chưa có gate mọi route mới phải thuộc ma trận. |
| Trung bình — ADM-02 | Khóa ACTIVE→FROZEN; audit có người/thời gian/FROZEN nhưng không ACTIVE. | Lưu trạng thái trước và sau trong audit thay đổi admin. |
| Trung bình — DSH-01 | Bấm Show balance, reload trở lại ẩn. Home dùng accounts[0]; total_balance từ API không được render. | Nhớ lựa chọn ẩn/hiện và tổng số dư nhiều tài khoản theo PDF. |
| Trung bình — AI-02 | Tool schema chỉ có get_recent_transactions(limit≤20) và get_transaction_status(id). | Tool lọc ngày/người nhận, tổng hợp đầy đủ kỳ; không chỉ lấy20 giao dịch gần nhất. |
| Trung bình — AI-12 | Trong khi gửi, textbox bị khóa, không có Stop/Cancel. | Hủy có tác dụng xuống backend; text streaming đúng tiêu chí. Hiện chỉ SSE progress và final answer sau filter. |
| Chưa đạt nghiệm thu nghiên cứu — AI-14/PI | Dữ liệu đã đo: baseline Qwen90%, Llama72%; chỉ1 utility repeat, temperature0.2, hai Ollama model. | Ngưỡng85% chưa đạt cho Llama; PDF yêu cầu3 repeats/temperature0, một API model và chấm cả câu trả lời. Lab hiện đo source-ingestion, chưa test toàn pipeline poisoning thật. |

RAG lần mới truy xuất đúng tài liệu nhưng câu trả lời không chứa mã citation; nguồn chỉ có trong View trace. AI-11 vì vậy được đánh dấu Một phần. Nghiên cứu1.790 observations trước được kiểm tra lại metadata/source hash, **không chạy lại toàn ma trận** trong audit này. ASR0 của corpus cũ không chứng minh đã đạt thiết kế mới; thiếu CI95% và rerun cùng seed theo PI-06. Corpus có35 case/7 vector nhưng direct chỉ5, trong khi PDF chỉ định6.

## Khác biệt đặc tả cần thống nhất

- AUTH-03: code từ chối extra role/balance bằng422; PDF nói bỏ qua rồi tạo customer0. Cả hai giữ ranh giới quyền, khác response contract.
- ADM-03: phí khóa khi tạo draft, nên admin đổi phí không đổi draft cũ. PDF mới yêu cầu áp dụng ở confirm kế tiếp. Không tự đổi mức phí khách đã xem khi đang audit.
- AI-13: delegated token bị chặn bằng401 do sai audience; PDF ghi403. Không có bằng chứng bypass confirm/admin.
- NF-07: UI/PDF đang dùng định dạng English12,500,000 VND theo lựa chọn UI trước; PDF yêu cầu12.500.000 ₫. Thời gian transaction detail đã dùng múi giờ Việt Nam.

## Độ phủ theo 121 ca

| Phân loại | Số ca |
|---|---|
| Đã kiểm chứng | 82 |
| Khác đặc tả | 4 |
| Một phần / thiếu bằng chứng | 24 |
| Chưa đạt | 10 |
| Chưa kiểm chứng | 1 |

[Ma trận đủ121 mã và test/file tương ứng](CASE_MATRIX.md) · [CSV để theo dõi](CASE_MATRIX.csv). Đây là số ca của tài liệu, không phải phép cộng số function pytest. Một ca PDF có thể cần nhiều test; một test có thể cung cấp bằng chứng cho nhiều ca. Phân loại Một phần không có nghĩa toàn tính năng chưa làm.

Các khoảng chưa đủ bằng chứng đáng chú ý: all-route RBAC và mass assignment; full XSS/secret-log corpus; mẫu savings tính tay theo nhiều ngày; time/round-budget của agent; API-model evaluation; axe-core. Axe-core chưa có trong dependencies và không được tự cài. Các scan dependency trước vẫn còn advisories; không nâng thành trạng thái security gate đạt.

## Lệnh và bằng chứng

```powershell
.\backend\.venv\Scripts\python.exe scripts/financial-coverage.py
cd frontend
npm run test:components
npm run test:e2e
```

Tái hiện các khoảng thiếu trên DB pytest tạm, từ root repo:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest docs/release/acceptance-audit/test_requirements.py -q --tb=short --show-capture=no
```

Bộ probe cố ý còn đỏ ở14 điểm đã báo cáo, không đổi expectation để làm xanh. Không đưa bộ đỏ này vào CI hiện có trong lượt kiểm thử. [Log probe](requirements.log), [JUnit](requirements.xml), [backend](backend.log), [component](components.log), [E2E/build](browser.log), [load/restore](load-result.json), [restart](restart-result.json), [UI observations](browser-observations.json), [agent](real-agent.json).

`aef check .` không chạy được vì repo không có engineering.json; đây là gate chưa cấu hình, không được ghi pass. Đã chạy trực tiếp các script thật ở trên. CI remote, review độc lập và pentest không được thực hiện trong lượt này. Kết quả là kiểm thử local và đối chiếu yêu cầu, không phải chứng nhận không còn lỗ hổng.
