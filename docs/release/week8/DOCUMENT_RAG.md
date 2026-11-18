# Document RAG

## 1. Mối đe dọa

PDF, TXT, Markdown và tên file là dữ liệu do người dùng cung cấp, không phải chỉ thị đáng tin. Rủi ro gồm lệnh ẩn, đổi người nhận tiền, URL lừa đảo, mã giả tự viết, lộ PII, dò tài liệu của người khác, file nén bất thường và model không khả dụng. Bộ fixtures dùng dữ liệu giả, gồm canary riêng của Bob.

## 2. Kỹ thuật

Bank API sở hữu upload, SQLite, trích xuất, screening, embedding và cosine retrieval. Agent chỉ gọi tool đọc `ask_document(document_id, question)` qua gateway hiện có; không có DB, khóa hay tool ghi mới. Migration 21 thêm documents/doc_chunks; mọi truy vấn dữ liệu nằm trong Repository và lọc owner từ session.

Trong Assistant, nút kẹp giấy mở “My documents” ngay cạnh ô chat. Có thể chọn file hoặc kéo PDF, TXT hay Markdown vào vùng chat, rồi bấm Upload document. Tài liệu Ready có thể được dùng để hỏi trong cuộc trò chuyện hiện tại. Nút ảnh QR và thao tác thả ảnh dùng bộ đọc QR hiện có, mở thông tin để kiểm tra trước khi sang màn chuyển tiền. Giao diện dùng lại Field, card, Sheet và button hiện có.

## 3. Cơ chế

1. Xác thực trước khi đọc body; giới hạn upload 10 lượt/5 phút, 5 MiB, 50 trang, 200 chunks và 20 tài liệu đang lưu/người dùng. Multipart giữ trong RAM, không spool file gốc ra đĩa.
2. Magic PDF hoặc UTF-8 hợp lệ; không tin Content-Type. Từ chối executable/binary, PDF hỏng, mật khẩu, không có text, hoặc quá giới hạn. pypdf có giới hạn giải nén, cây trang và XObject. Không OCR.
3. Chuẩn hóa NFKC, chunks 800 ký tự, overlap 100. Loại mã giả do nguồn tự viết trước P; mã do server cấp mới được khôi phục. Nhận diện thực thể trên toàn tài liệu trước khi xử lý từng chunk để bảo vệ cả lần nhắc lại không kèm nhãn. P chạy trước bộ phát hiện, embeddings, isolated reader và main model.
4. Quét tên file và từng chunk bằng chuỗi source_screen hiện có. Nguồn độc: quarantined. Hạ tầng không khả dụng: scan_failed. Re-upload đúng bytes của tài liệu scan_failed để thử lại, dùng lại slot của chính user.
5. Chỉ ready được retrieve; top-k=4, trong đúng tài liệu/owner. Kiểm tra vector hữu hạn, số chiều, model và kiểm tra lại trạng thái sau await để chặn xóa trong lúc đọc.
6. C/D dùng model cách ly không tool, JSON schema chặt: found, answer ≤500 ký tự, citations thuộc tập vừa đọc, amounts/dates đúng định dạng và có trong nguồn. Schema sai/model lỗi: found=false, DENY, event. A/B đưa chunks đã qua P cho main model; B có spotlighting. Cấu hình chỉ đến từ policy JSON.
7. FIELD_TRUST đánh dấu text, answer, filename_display. Nhãn hội thoại chỉ tăng lên UNTRUSTED. Token cho yêu cầu chỉ hỏi tài liệu không có tool ghi khi intent binding bật. Yêu cầu hỗn hợp vẫn ràng buộc người nhận và số tiền từ lời user.
8. Traces/security_events chỉ giữ hash, ID, quyết định, rule; không giữ source prose. Câu trả lời được lưu ở hội thoại để user đọc. Sau khi hủy vault cuối lượt, nội dung assistant cũ trong hội thoại đã đọc tài liệu không được phát lại cho model; phải đọc lại nguồn qua gateway.

## 4. Thuộc tính bảo đảm / không bảo đảm

Owner filtering, UUID, session authentication, kiểm tra trạng thái và P áp dụng ở mọi cấu hình. Thiếu luật explicit ask_document gặp NO_MATCHING_POLICY; wildcard không cấp quyền đọc. DELETE xóa mềm metadata và xóa chunks; câu trả lời cũ vẫn trong hội thoại.

Không bảo đảm detector bắt mọi prompt injection hay model luôn trả lời đúng. Tấn công tự nhiên có thể lọt 1b; bảo vệ hành động đến từ capability, T4-bind, policy và xác nhận của user. A/B là đối chứng có chủ đích, không được diễn giải là cấu hình production an toàn.

Nhãn UNTRUSTED theo hội thoại làm giao dịch hợp lệ ở lượt sau cộng 40 điểm rủi ro khi risk_signals bật, ngoài điểm nền và người nhận mới. Không có hành động tiền tệ nào được hoàn tất bằng ask_document. Schema hợp lệ không chứng minh mọi câu chữ đều đúng: citations và số tiền là kiểm tra cấu trúc/nguồn, không phải chứng minh ngữ nghĩa.

Không OCR; không lưu file gốc; không vector DB; không tự tải model. Explicit mock có embeddings mang nhãn mock-only-document-embedding và reader giả lập; tuyệt đối không dùng làm số liệu model thật. Ingest hiện đồng bộ theo request; tài liệu dài cần chờ quét xong.

## 5. Cơ sở nghiên cứu

- [Hines và cộng sự, Spotlighting (2024)](https://arxiv.org/abs/2403.14720): biến đổi đầu vào để biểu thị nguồn gốc, giúp model phân biệt dữ liệu ngoài với chỉ thị. Kết quả của bài báo dùng các model GPT; không suy rộng tỷ lệ thành công đó sang Qwen hay bộ fixtures này.
- [Microsoft, bảo vệ trước indirect prompt injection](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks): kết hợp biện pháp xác suất và kiểm tra xác định. Áp dụng ở đây: screening hỗ trợ phát hiện, còn quyền đọc, owner và tham số giao dịch được kiểm tra trong code.
- [FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/): multipart cần python-multipart. Parser có giới hạn riêng để không lưu nguyên file lên đĩa.
- [pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html): không phải OCR; extraction có thể tiêu tốn bộ nhớ, nên giới hạn cả dữ liệu giải nén.
- [Ollama embed API](https://docs.ollama.com/api/embed): truncate=false tránh âm thầm mất phần cuối văn bản.

Các tầng có sẵn, source_screen, Prompt Guard, T4-bind và provenance được ánh xạ trong DOCRAG_DISCOVERY.md; không thêm lớp quyền hạn cho model.

## 6. Vì sao phù hợp

Quy mô demo tối đa 20 × 200 chunks/user phù hợp SQLite và numpy brute-force. Giữ nguyên FastAPI/React, package manager và giao diện. Tách rõ lỗi hạ tầng với phát hiện nguồn độc giúp đánh giá không ghi ERROR thành PASS. Bộ dữ liệu tái tạo được, kiểm tra ledger và chạy trên DB disposable tránh ảnh hưởng demo đang dùng.

## 7. Hiện trạng và vận hành

Các endpoint: POST/GET /api/documents; GET/DELETE /api/documents/{document_id}. Tool chỉ qua /api/agent/tools với delegated token, không có endpoint đọc nội bộ bỏ qua gateway. UI: /documents; vào từ nút My documents trên Assistant.

Chạy kiểm tra:

```powershell
& backend/.venv/Scripts/python.exe scripts/document-rag-check.py
# Thêm model thật bằng runtime đã được provision:
$env:PROMPT_GUARD_MODEL_PATH = 'absolute/path/to/local/prompt-guard-2-86m'
$env:QUARANTINED_LLM_MODEL = 'qwen2.5:7b'
& backend/.venv/Scripts/python.exe scripts/document-rag-check.py --live-python 'absolute/path/to/runtime/python.exe' --baseline-project 'absolute/path/to/pre-feature-checkout' --harness-dir 'absolute/path/to/existing/week8-pentest'
```

Runner xuất JUnit, HTML và logs vào .local/document-rag-evidence. Thiếu runtime hoặc harness được ghi BLOCKED; mã thoát 2 là thiếu bằng chứng, 1 là FAIL/ERROR, 0 là toàn bộ PASS. Model/runtime không tự cài. Mặc định isolated reader là llama3.2:3b; phép đo dùng model đã nêu trong report, không suy rộng sang model khác.

Ollama phải đang chạy; dùng `--ollama-url` để chọn địa chỉ của môi trường. Tiêu chí đạt của ma trận giữ nguyên các trường hợp tấn công thành công ở A/B làm đối chứng; không coi đó là lỗi của cấu hình C/D. Owner filtering, P và benign utility vẫn phải đạt ở cả bốn cấu hình. Lỗi hạ tầng hoặc thiếu số lượt luôn làm phép đo chưa đạt.

`scripts/document-rag-live.py` chạy 3 lượt/cấu hình trên bank/agent disposable. `scripts/document-rag-baseline.py` sao chép harness A–J hiện có vào thư mục disposable và chỉ thay URL/DB/root, không chạm DB demo. Chạy script này cho revision trước và sau rồi so sánh kết quả theo ID.

Seed mới: `python scripts/seed_realistic.py --output .local/seed/new.sqlite3`. Kiểm tra: `python scripts/check-document-seed.py .local/seed/new.sqlite3`. Cờ --cleanup-pentest-fixture chỉ nhận DB có manifest synthetic, từ chối giao dịch có posting; việc xóa fixture display-only và khôi phục trigger nằm trong cùng transaction.

Kết quả đã đo, giới hạn và trạng thái review được ghi trong FUNC_API_TEST_REPORT.md. Không merge main từ nhánh này; nhóm review PR.

Nếu server dừng giữa lúc upload, xóa mục processing còn lại rồi upload lại. Khi đo model thật, dùng checkout bất biến: không sửa mã nguồn trong lúc server đang chạy vì Python có import muộn.
