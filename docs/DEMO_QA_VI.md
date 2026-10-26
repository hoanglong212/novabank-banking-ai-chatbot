# Chuẩn bị hỏi đáp khi demo NovaBank

Tài liệu ôn tập cho người thuyết trình. Mỗi câu có câu trả lời ngắn (nói được trong 1–2 câu) và chi tiết để dẫn chứng nếu bị hỏi sâu. Số liệu lấy từ code và báo cáo kiểm thử trong `docs/`.

---

## 0. Ba câu cần thuộc lòng

1. **Ai quyết định cho phép gọi tool?** `PolicyGateway` độc lập ([gateway.py](../backend/app/gateway.py)), không phải LLM. Mọi tool đều đi qua `ToolDispatcher.run → PolicyGateway.authorize → chỉ khi ALLOW mới chạy`.
2. **Đây có phải ngân hàng thật / bảo mật thật không?** Không. Đây là demo nghiên cứu, dữ liệu hoàn toàn giả, token đăng nhập là công khai, không được đưa lên Internet.
3. **Đã tích hợp gateway thật của Nhóm 10 chưa?** Chưa. Chỉ có adapter với hợp đồng API *đề xuất* (`POST /authorize`), sẽ chỉnh khi có đặc tả thật. Gateway lỗi hoặc không phản hồi thì **từ chối** (fail closed).

---

## 1. Tổng quan dự án

**Dự án làm gì?**
Chatbot hỗ trợ khách hàng cho một ngân hàng giả tên NovaBank. Người dùng hỏi FAQ, xem số dư, tra giao dịch, tạo phiếu hỗ trợ. Trọng tâm là chứng minh **lớp kiểm soát quyền đứng giữa AI agent và tool**, dùng cho đề tài Runtime Security Gateway.

**Vì sao chọn ngân hàng?**
Đây là lĩnh vực mà việc agent gọi sai tool (đọc tài khoản người khác, chuyển tiền) gây hậu quả rõ ràng, nên dễ minh họa giá trị của gateway.

**Phạm vi?**
Bản MVP cho giai đoạn 13–15/10/2026. Có 4 tool mô phỏng, 2 người dùng demo (Alice, Bob), 2 chế độ chạy (mock / Ollama).

**Không làm gì?**
Không chuyển tiền, không có OTP, không có API ngân hàng thật, không có dữ liệu khách hàng thật, không có đăng nhập thật.

---

## 2. Kiến trúc và công nghệ

**Stack?**
- Frontend: React 19 + TypeScript + Vite + Tailwind, icon lucide-react.
- Backend: Python FastAPI + Pydantic + httpx.
- Lưu trữ: SQLite (4 bảng: `conversations`, `messages`, `tool_events`, `support_tickets`).
- LLM: Ollama chạy local, model `llama3.2:3b`, `temperature=0`.

**Luồng xử lý một tin nhắn?**
```
UI → FastAPI (xác định user từ bearer token)
   → Agent (mock hoặc Ollama) đề xuất tool + tham số
   → ToolDispatcher → PolicyGateway.authorize → ghi audit ALLOW/DENY
   → chỉ khi ALLOW: chạy tool mô phỏng
   → ứng dụng soạn câu trả lời từ kết quả tool → lưu SQLite → trả về UI
```

**Vì sao chạy LLM local (Ollama) mà không dùng API đám mây?**
Không phải gửi dữ liệu ra ngoài, không tốn phí, chạy offline được, và có thể thay model khác.

**Vì sao chọn model 3B nhỏ?**
Để chạy được trên laptop thông thường. Đổi lại, model này chọn tool kém ổn định và tiếng Việt yếu hơn, nên ứng dụng phải ràng buộc chặt (xem mục 4).

**Chế độ `mock` là gì?**
Chạy theo kịch bản cố định, **không phải AI sinh văn bản**. Dùng để demo khi không có Ollama/GPU. Không được dùng mock để kết luận gì về chất lượng LLM.

**Ngữ cảnh hội thoại?**
Mỗi lượt gửi tối đa 24 tin nhắn gần nhất cho model. Toàn bộ lịch sử vẫn nằm trong SQLite, refresh trang hay khởi động lại backend vẫn còn.

**Chạy demo thế nào?**
`powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Setup -Mode mock`, sau đó mở `http://127.0.0.1:8080`. Lệnh này build UI và chạy cả UI lẫn API trên một cổng. Có thêm bản Docker cho chế độ mock.

---

## 3. Bảo mật và phân quyền (câu hỏi trọng tâm)

**4 tool và luật phân quyền?**

| Tool | Luật |
|---|---|
| `search_banking_faq` | Cho phép nếu tham số hợp lệ |
| `get_account_balance` | Tài khoản phải thuộc về user đang đăng nhập |
| `get_transaction_status` | Giao dịch phải thuộc về user |
| `create_support_ticket` | Kiểm tra dữ liệu + nằm trong allowlist + user phải yêu cầu rõ ràng |

Tool nằm ngoài allowlist (ví dụ `transfer_money`) bị từ chối với `UNKNOWN_TOOL`.

**Nếu LLM bị prompt injection và cố gọi tool đọc tài khoản Bob thì sao?**
Gateway vẫn chặn (`ACCOUNT_NOT_OWNED`, `executed=0`). Quyền được kiểm tra dựa trên danh tính lấy từ token phía server, không dựa trên lời model. Đã có test chứng minh việc phân quyền không phụ thuộc vào output của model.

**Agent có đường nào bỏ qua gateway không?**
Trong code hiện tại, đường thực thi duy nhất là `ToolDispatcher.run`, và đường này luôn gọi `authorize` trước. Đã review source và có test. Tuy vậy, điều này **không chứng minh hình thức** rằng mọi kiểu bypass đều không thể xảy ra, và không áp dụng cho agent bên ngoài.

**Biết một conversation ID thì mở được hội thoại của người khác không?**
Không. Mọi route đọc/xóa đều so chủ sở hữu với user lấy từ token. Bob đọc hội thoại của Alice sẽ nhận 404.

**Ghi log (audit) những gì?**
Mỗi quyết định gồm tool, tham số, ALLOW/DENY, mã lý do, và tool có thực sự chạy hay không. Khi model đề xuất sai tool, hệ thống ghi lại việc bị từ chối nhưng không lưu tham số của đề xuất đó.

**Panel "Policy test" là gì?**
Chạy thử (dry-run): chỉ hỏi gateway ALLOW hay DENY, **không bao giờ chạy tool**, kể cả khi ALLOW. Vì vậy một bản ghi `ALLOW / executed=0` không có nghĩa là đã thực hiện hành động.

**Những gì gateway chưa giải quyết được?** (nên chủ động nói ra)
- Chưa kiểm tra *ý định ngữ nghĩa*: một lời gọi hợp lệ, đúng chủ sở hữu, vẫn có thể không phải điều user thực sự muốn.
- Chưa kiểm soát chuỗi hành động (sequence) và luồng dữ liệu (taint).
- Chưa chống được việc lộ dữ liệu qua câu trả lời cuối cùng.
- Audit log chưa được bảo vệ (chưa che dữ liệu nhạy cảm, chưa đảm bảo toàn vẹn).

**Token demo nằm sẵn trong frontend, chẳng phải lỗ hổng sao?**
Đúng, và đó là chủ ý để đổi user nhanh khi demo. Khi triển khai thật cần OIDC và xác thực JWT ở backend. Điều này đã ghi rõ trong README và [SECURITY_AND_LIMITATIONS.md](SECURITY_AND_LIMITATIONS.md).

---

## 4. AI làm được gì thật (dễ bị hỏi vặn)

**LLM có tự quyết định gọi tool nào không?**
Không hoàn toàn, và cần nói thẳng. Ứng dụng (`bind_request` trong [banking_workflow.py](../backend/app/banking_workflow.py)) nhận diện thao tác từ câu của user bằng từ khóa, rồi **chỉ đưa schema của tool đó** cho Ollama. ID tài khoản/giao dịch lấy từ chính câu user nhập, không lấy từ model. Câu trả lời cuối do ứng dụng soạn từ kết quả tool. Đây là ứng dụng "hybrid có kiểm soát", **không phải benchmark năng lực suy luận của model**.

**Vì sao không để model tự do?**
Kiểm thử ban đầu với model 3B: model tự bịa account ID (`123456`, `DemoAcc123`), trả JSON thô ra màn hình, và hỏi xin số thẻ/số điện thoại khi tạo ticket. Vì vậy phải ràng buộc lại.

**`response_source` là gì?**
Nhãn cho biết câu trả lời được tạo theo đường nào:
- `ollama_tool`: model đề xuất đúng tool và đúng tham số.
- `ollama_tool_bound`: đúng tool nhưng ứng dụng thay tham số bằng giá trị lấy từ câu user.
- `application_fallback`: model không đề xuất hoặc đề xuất lỗi, ứng dụng tự chạy thao tác (vẫn qua gateway).
- `application_template`: câu trả lời cố định, không gọi tool.
- `mock`: chế độ offline.

Trong 33 lượt chạy thật: 15 `ollama_tool`, 15 `ollama_tool_bound`, 3 `application_template`, 0 `application_fallback`.

**Ollama tắt thì sao?**
Trả lỗi 503 rõ ràng, không giả vờ có câu trả lời. `/api/ready` kiểm tra model đã cài và truy cập được hay chưa.

**Hỏi ngoài phạm vi (ví dụ phí chuyển 10 triệu)?**
Tìm trong FAQ soạn sẵn. Nếu không có thì nói không có thông tin, **không bịa** phí, hạn mức hay quy định.

**Có hỗ trợ tiếng Việt không?**
Giao diện và câu trả lời mới đều bằng tiếng Anh. Bộ nhận diện từ khóa có hiểu tiếng Việt không dấu/có dấu (ví dụ "số dư", "chuyển 3 triệu"). Chất lượng hội thoại tiếng Việt với model thật chưa được đo.

**Có streaming không?**
Chưa. UI hiển thị trạng thái đang tải rồi nhận nguyên câu trả lời một lần.

---

## 5. Kiểm thử và kết quả

**Đã test thế nào?**
- Backend: 51 test pytest chạy pass (lưu lịch sử, tách biệt 2 user, ALLOW/DENY, phân quyền độc lập với model, giả lập giao thức Ollama).
- 15 kịch bản ứng dụng (T01–T15) chạy với Ollama thật, qua API và trình duyệt Edge.
- 8 kịch bản quan trọng chạy lặp 3 lần.

**Kết quả?**
- Lần đầu (baseline): **10/15 pass**. Các lỗi: lời chào ra JSON thô, thiếu số tiền giao dịch, ticket không hiện mã, model bịa account ID, UI báo lỗi khi đổi user Alice→Bob.
- Sau khi sửa: **15/15 pass**, 8 ca lặp 3/3. Bằng chứng nằm trong các file JSON ở `docs/`.

**Có điểm yếu nào trong cách test?**
Có, nên tự nói ra: chưa có người review độc lập; chưa chạy bộ 20 câu diễn đạt khác nhau; chỉ test trên Edge; nhận diện ý định dựa trên từ khóa nên câu diễn đạt lạ có thể không nhận ra.

---

## 6. Kịch bản demo nhanh (tham khảo [DEMO_SCRIPT.md](DEMO_SCRIPT.md))

| Hỏi | Kết quả mong đợi |
|---|---|
| "What is VietQR?" | FAQ, `search_banking_faq — ALLOW` |
| "What is my account balance?" | `ACC-ALICE-001`, 12,500,000 VND |
| "Do I have enough money to transfer 3 million?" | Đủ, và nói rõ **chưa chuyển tiền** |
| "Check transaction TX-1002" | PENDING, 950,000 VND |
| "Check transaction TX-2001" (của Bob) | DENY `TRANSACTION_NOT_OWNED`, không lộ dữ liệu |
| Policy test: `ACC-BOB-001` / `ACC-ALICE-001` | DENY / ALLOW, cả hai `executed=false` |
| Refresh, đổi Alice → Bob → Alice | Lịch sử còn nguyên, mỗi người chỉ thấy hội thoại của mình |

**Phương án dự phòng:** nếu Ollama chậm hoặc lỗi, chạy lại với `-Mode mock` và nói rõ đó là chế độ kịch bản.

---

## 7. Câu hỏi về hướng phát triển

**Bước tiếp theo?**
1. Thay token demo bằng OIDC/JWT thật.
2. Kết nối gateway thật của Nhóm 10 và viết contract test.
3. Đo độ chính xác chọn tool và chất lượng tiếng Việt với model thật (bộ 20 câu).
4. Thêm streaming (SSE).
5. Cải thiện truy xuất FAQ (RAG) và trích dẫn nguồn từ chính sách được duyệt.
6. Thí nghiệm so sánh bộ phát hiện PII và chạy trọn vòng qua gateway.

**Muốn dùng thật cần thêm gì?**
Xác thực thật, CSDL thay SQLite (hỗ trợ đồng thời, sao lưu, mã hóa), giới hạn tần suất (rate limit), audit log có che dữ liệu và chống sửa đổi, kiểm thử prompt injection với model thật, và rà soát pháp lý/tuân thủ.

**Có thể đổi sang model lớn hơn không?**
Được. Chỉ cần sửa `OLLAMA_MODEL` trong `backend/.env` rồi khởi động lại. Gateway và luật phân quyền không đổi.

**Code có sao chép từ repo khác không?**
Không. Code tự viết, chỉ tham khảo ví dụ chính thức của các framework.

---

## 8. Mẹo trả lời

- Khi bị hỏi "AI có thông minh không", tránh nói quá. Hãy nói: *"Giá trị chính là lớp kiểm soát: kể cả khi AI sai, tool vẫn không chạy sai."*
- Chủ động nêu giới hạn trước khi bị hỏi; người xem kỹ thuật sẽ đánh giá cao điều này.
- Khi bị hỏi bằng chứng, mở panel Tool activity / Testing insights để chỉ ALLOW/DENY và `executed`.
