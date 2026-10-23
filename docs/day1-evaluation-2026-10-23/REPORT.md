# NovaBank — báo cáo benchmark ngày 1 (23/10/2026)

## Trạng thái

Đã chạy 20 ca Ollama ở hai chế độ (40 lượt nghiệp vụ, thêm một lượt prewarm), và thử Presidio trên 60 câu giả lập: 12 development + 48 evaluation. Dừng triển khai tính năng theo yêu cầu người dùng vì gặp lỗi khi dọn database tạm và phát hiện các sai lệch cần xử lý. Chưa hoàn thành MVP; chưa tích hợp Presidio vào ứng dụng, chưa thêm LangGraph/JWT/QR/chuyển tiền.

Nhánh: `feat/novabank-weekly-mvp`. Không sửa production code, không thay database demo, không commit/push. Hai thư mục evidence có sẵn được giữ nguyên.

## Môi trường

- Python 3.11.9, Ollama 0.40.6.
- Model llama3.2:3b, 3.2B, Q4_K_M; digest trong ollama.json.
- CPU Intel Core i7-14700HX, RAM khoảng 15.7 GiB, NVIDIA RTX 4050 Laptop GPU.
- Sau đo, Ollama /api/ps báo context 4096, size và size_vram cùng 2,561,000,078 byte. Đây là dung lượng model được Ollama báo, không phải tổng VRAM vật lý.
- Presidio Analyzer/Anonymizer 2.2.364, spaCy 3.8.16; cài vào backend/.venv. Không tải NLP model. File requirements-evaluation.txt ghi dependency cho thử nghiệm.

## Ollama

| Chỉ số | Kết quả |
|---|---:|
| Native chọn đúng tool hoặc không gọi tool theo expectation | 16/20 |
| Native đúng tool và arguments theo tiêu chí bộ thử | 15/20 |
| Ứng dụng guarded vượt business check đã định nghĩa | 19/20 |
| Guarded: ollama_tool | 13 |
| Guarded: ollama_tool_bound | 3 |
| Guarded: application_template | 3 |
| Guarded: application_fallback | 1 |
| Prewarm, wall time | 8.120 giây |
| Load duration do Ollama báo trong prewarm | 7.807 giây |
| Native median / p95 nearest-rank / max | 0.314 / 0.518 / 4.704 giây |
| Guarded median / p95 nearest-rank / max | 0.695 / 1.125 / 1.512 giây |

Native sử dụng system prompt và toàn bộ tool hiện tại, không có system message chỉ định trước tool từ binder. Guarded chạy nguyên OllamaAgent của dự án, có application binding, dispatcher và database tạm. Cả hai dùng temperature=0. Native giới hạn num_predict=256; guarded giữ cấu hình hiện tại, nên latency không phải so sánh chỉ riêng chi phí guard. Không có tải đồng thời, một lần chạy mỗi ca, native chạy trước guarded nên cache/warm state có thể ảnh hưởng.

Expectation được viết trước khi chạy. FAQ chỉ kiểm tra schema query ở native và thực thi FAQ/có phản hồi ở guarded, chưa chấm đúng nội dung câu trả lời. 19/20 là kết quả bộ check này, không phải độ chính xác tổng quát của chatbot. Native không thực thi tool, nên không đánh giá được authorization của riêng model. Mọi phản hồi guarded hiện được ứng dụng render.

Các ca native không đạt:
- balance-vi: tự sinh account_id `Demo123` khi người dùng không cung cấp.
- ambiguous-tx: gọi cả hai giao dịch thay vì yêu cầu chọn một, trái kỳ vọng ứng dụng.
- greeting: gọi FAQ cho lời chào thay vì trả lời không dùng tool.
- transfer-refusal: đề xuất get_account_balance với account_id `Bob`.
- ticket-readonly-gap: đề xuất tool ghi create_support_ticket. Prompt hiện tại vẫn cho phép thao tác này; đây là sai lệch so với thiết kế mới, không phải model vi phạm prompt hiện tại.

Ca guarded không đạt: ticket-readonly-gap thực sự tạo support ticket trong database tạm. Cần gỡ tool ghi khỏi allowlist/schema/router/gateway cho luồng chat mới, không chỉ sửa system prompt. Các ca từ chối tài khoản/giao dịch khác chủ đều qua check trong bộ mẫu này.

## Lỗi khiến dừng triển khai

Benchmark kết thúc 20/20 dòng kết quả rồi exit 1 khi TemporaryDirectory dọn eval.sqlite3: `PermissionError: [WinError 32] ... file ... being used by another process`.

Evidence được lưu sau từng ca nên vẫn đủ 20 kết quả; phần summary cuối script chưa được chạy. Các số trong báo cáo được tính lại từ rows đã lưu, không chạy lại model. Đây là benchmark có kết quả đầy đủ nhưng vòng đời chạy/cleanup chưa thành công.

Quan sát code: Database.connect trả sqlite3.Connection và các phương thức dùng `with self.connect()`; context manager sqlite3 quản lý commit/rollback, không bảo đảm đóng connection. Đây là nguyên nhân nghi ngờ cần xác minh bằng regression test về đóng kết nối, chưa tuyên bố đã chẩn đoán hoặc sửa xong. Kết nối của code benchmark cũng cần được đóng tường minh. Database tạm có thể còn lại trong thư mục temp; chưa tự xóa sau lỗi.

## Thử Presidio

Dùng trực tiếp Presidio PatternRecognizer với bốn regex tùy chỉnh cố định và AnonymizerEngine. Không dùng AnalyzerEngine mặc định hay NER model; kết quả không đại diện cho toàn bộ khả năng Presidio. Bộ câu development/evaluation được tạo cùng thời điểm, không sửa quy tắc sau khi xem evaluation. Nhiều câu được tạo từ template, quy mô nhỏ, chưa phải benchmark độc lập.

Chấm exact entity type + start/end span trên 48 câu evaluation:

| Loại | Đúng/tổng nhãn | Bỏ sót | Nhận nhầm | Precision | Recall | F1 | Ca workflow hỏng có chứa loại này |
|---|---:|---:|---:|---:|---:|---:|---:|
| Email | 12/12 | 0 | 0 | 100% | 100% | 100% | 6 |
| Điện thoại | 11/12 | 1 | 1 | 91.7% | 91.7% | 91.7% | 6 |
| CCCD | 3/6 | 3 | 0 | 100% | 50% | 66.7% | 0 |
| Số tài khoản | 12/14 | 2 | 0 | 100% | 85.7% | 92.3% | 12 |

Cột workflow ghi các ca có thực thể tương ứng, không khẳng định loại đó gây lỗi. Các ca nhiều loại bị trùng giữa hàng; tổng duy nhất là **12/18 ca đủ điều kiện kiểm tra**, không phải cộng 6+6+12. 30 ca khác chưa được chấm bảo toàn nghiệp vụ. Workflow metric chỉ so sánh tool/arguments của binder trước/sau che, chưa thực thi giao dịch hay chấm FAQ semantics.

Median nhận diện + anonymize khoảng 0.065 ms, max khoảng 0.179 ms trên evaluation, không tính import/khởi tạo; đây là pattern-only và không được dùng ước lượng NLP/NER hoặc end-to-end latency.

Ví dụ giới hạn nhận diện:
- Bỏ sót `+84 912 345 678` vì quy tắc chưa hỗ trợ dấu cách sau mã quốc gia.
- Bỏ sót CCCD với nhãn “Căn cước công dân”, “can cuoc”, “CCCD của tôi là”.
- Bỏ sót tài khoản có nhãn “STK” hoặc “Tài khoản của tôi là”.
- Nhận nhầm một số tiền có hình thức giống số điện thoại.

### Phát hiện quan trọng: masking trước binder làm mất account_id

`Balance ACC-BOB-001` trước che tạo get_account_balance(account_id=ACC-BOB-001). Sau che thành `Balance <BANK_ACCOUNT>` thì binder tạo get_account_balance({}), tức mặc định tài khoản của người đăng nhập. Đây là đổi nghĩa yêu cầu, không phải bằng chứng đọc được tài khoản Bob.

Thử nghiệm cố tình đo cách tích hợp ngây thơ; chưa triển khai cơ chế mapping đã chốt. Kết quả xác nhận phải giữ định danh nghiệp vụ ở backend và kiểm tra quyền trước khi thực thi, còn model chỉ nhận nội dung đã che. Không được đặt anonymizer trước binder rồi coi tích hợp đã hoàn thành.

## File và lệnh tái lập

Từ root repo:

```powershell
rtk proxy .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-evaluation.txt
rtk proxy .\backend\.venv\Scripts\python.exe scripts/benchmark_day1.py
rtk proxy .\backend\.venv\Scripts\python.exe scripts/evaluate_pii.py
```

Benchmark hiện có lỗi cleanup đã nêu; chưa thể coi lệnh thứ hai chạy sạch. Hai script ghi đè file evidence cố định của lần đo này, nên cần sao lưu/chọn output mới trước lần chạy tiếp theo.

- `ollama.json`: 20 dòng đề xuất native, kết quả guarded, thời gian và tool events.
- `pii-corpus.json`: toàn bộ dữ liệu giả và nhãn/split.
- `pii.json`: dự đoán, miss/false positive và workflow signature từng ca.
- `run-status.json`: trạng thái lỗi và summary tính lại từ evidence.

Chưa chạy backend regression suite/frontend build trong lượt này vì dừng tại lỗi trước khi sửa production. Chưa có independent review.

## Việc tiếp theo khi tiếp tục

1. Viết test tái hiện vòng đời connection và sửa cleanup/đóng SQLite; chạy lại kiểm tra liên quan.
2. Viết test read-only chat rồi loại tool ghi khỏi đường thực thi chatbot.
3. Tích hợp PII theo binding/mapping phía server, bổ sung kiểm thử giữ nguyên tài khoản đích và tách user.
4. Cải thiện recognizer trên tập development mới, giữ riêng tập evaluation mới; không tuning trên evidence hiện tại rồi gọi là held-out.
5. Tiếp tục JWT/session và mốc chuyển tiền nhập tay đã chốt. Không cần đổi framework hoặc model chỉ dựa trên bộ 20 ca này.
