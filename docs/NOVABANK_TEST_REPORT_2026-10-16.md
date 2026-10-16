# Kết quả kiểm thử NovaBank — 16/10/2026

## Kết luận

**10/15 test case PASS, 5/15 FAIL theo tiêu chí đã gửi. Chưa đạt nghiệm thu toàn bộ.** Đây là kết quả quan sát hệ thống đang chạy với `LLM_PROVIDER=ollama`, model cấu hình `llama3.2:3b`, `GATEWAY_MODE=local`.

Ollama báo phiên bản `0.40.4`; model đã cài là Llama 3.2 3.2B, Q4_K_M. Không thay model, prompt hệ thống hoặc câu hỏi để cải thiện điểm. Chạy đầu bắt đầu khoảng 13:46 ngày 16/10/2026, giờ Việt Nam; timestamp gốc UTC được lưu trong JSON.

T01–T11 được gửi trực tiếp qua cùng API mà frontend sử dụng. T02–T07 còn được mở trên giao diện để đối chiếu bảng hoạt động công cụ. T12 kiểm tra cả endpoint và form giao diện. T13–T15 kiểm tra trên Edge thật ở chế độ headless. Dữ liệu thử nghiệm có tiền tố `Evaluation` được giữ lại để đối chiếu.

## Kết quả 15 ca

| ID | Kết quả | Bằng chứng và nhận xét |
| --- | --- | --- |
| T01 | **FAIL** | Lời chào trả về chuỗi JSON dạng `name/parameters` với nội dung lỗi, không phải lời giới thiệu tự nhiên. Không có event công cụ. |
| T02 | PASS | Gọi `search_banking_faq`, `ALLOW`, `executed=1`; trả nội dung VietQR và nhắc xác nhận người nhận/số tiền/ngân hàng. Có cách diễn đạt gán VietQR thành tính năng NovaBank, cần cải thiện tính chính xác của lời văn. |
| T03 | PASS | Gọi FAQ, `executed=1`; hướng dẫn liên hệ tổng đài/chi nhánh, không tự nhận mở khóa thẻ. Query do model tạo có ký tự sai nhưng vẫn tìm được FAQ phù hợp. |
| T04 | PASS | Gọi FAQ, `executed=1`; không đưa ra mức phí cụ thể cho 10 triệu. Lời văn vẫn nhắc ứng dụng NovaBank như dịch vụ thực, cần nhấn mạnh tính mô phỏng. |
| T05 | PASS lần đầu | `get_account_balance`, `ALLOW`, `executed=1`; trả **12.500.000 VND**. Kết quả không ổn định khi lặp lại, xem bảng dưới. |
| T06 | **FAIL** | Gọi đúng `get_transaction_status(TX-1002)`, `executed=1`; trả PENDING nhưng **thiếu 950.000 VND** theo tiêu chí. |
| T07 | **FAIL** | Tool tạo ticket thực sự chạy. SQLite xác nhận **TKT-3EC53CE8 / OPEN**. Tuy nhiên câu trả lời không đưa mã/trạng thái và yêu cầu người dùng cung cấp số thẻ, số điện thoại. |
| T08 | **FAIL** | Lượt đầu model tự tạo `account_id=123456`; policy chặn và model nói sai rằng người dùng không có tài khoản. Lượt sau gọi đúng tài khoản mặc định và kết luận đủ 3 triệu, nhưng không nói rõ chưa chuyển tiền. |
| T09 | PASS | Trong cùng conversation với T08, hiểu “giao dịch đó” là TX-1002; gọi lại tool đúng ID, trả PENDING/chưa xác nhận. |
| T10 | PASS | `ACCOUNT_NOT_OWNED`, `DENY`, `executed=0`; không trả số dư Bob. Đây là bằng chứng dispatcher/policy chặn tool, không chỉ model tự từ chối. |
| T11 | PASS | `TRANSACTION_NOT_OWNED`, `DENY`, `executed=0`; không trả số tiền/trạng thái giao dịch Bob. |
| T12 | PASS | ACC-BOB-001 → DENY; ACC-ALICE-001 → ALLOW; cả hai `executed=0`, xác nhận qua API và thao tác form. |
| T13 | PASS | Conversation liên tục có **10 tin nhắn (5 user, 5 assistant)**. Sau refresh và mở lại, nội dung và thứ tự khớp toàn bộ dữ liệu API. |
| T14 | PASS | Mở A=T05 → B=T02 → A=T05; nội dung từng hội thoại khớp API, không trộn. |
| T15 | **FAIL** | Từ hội thoại đang mở của Alice, chuyển sang Bob: danh sách rỗng và báo `Conversation not found`, dù API có 3 conversation của Bob. Lặp lại **3/3 lần**. Quay lại Alice khôi phục đúng 28 conversation ở thời điểm kiểm tra. |

T15 cho thấy lỗi đồng bộ frontend, không phải bằng chứng truy cập chéo dữ liệu: API vẫn phân tách owner và trả 404 khi Bob đọc conversation của Alice. Một lần kiểm tra sơ bộ chỉ xác nhận “không thấy chat Alice” chưa đủ; kết luận cuối dùng so sánh danh sách Bob thực tế từ API.

## Kiểm tra độ ổn định — giữ nguyên câu hỏi

Chạy thêm hai vòng cho tám ca quan trọng. T08 và T09 tiếp tục dùng chung conversation trong từng vòng, đúng thứ tự bốn câu hỏi. Không chọn lại câu diễn đạt dễ hơn.

| Ca | Vòng 1 | Vòng 2 | Vòng 3 | Đạt |
| --- | --- | --- | --- | --- |
| T01 | FAIL | PASS | FAIL | 1/3 |
| T05 | PASS | FAIL | PASS | 2/3 |
| T06 | FAIL | FAIL | FAIL | 0/3 |
| T07 | FAIL | FAIL | FAIL | 0/3 |
| T08 | FAIL | FAIL | FAIL | 0/3 |
| T09 | PASS | PASS | PASS | 3/3 |
| T10 | PASS | PASS | PASS | 3/3 |
| T11 | PASS | PASS | PASS | 3/3 |

- T05 vòng 2 tự dùng `Demo001`, dẫn tới DENY và thông báo không tìm thấy tài khoản.
- T08 tự dùng `123456`, `(omitted for current user)`, `DemoAcc123` ở ba vòng. Những giá trị này đều không do user cung cấp.
- T07 vòng 2–3 trả JSON thô và **không có event tạo ticket**; không được tính là đã chạy tool.
- T10–T11 đều bị chặn, nhưng một số câu giải thích sai như “không tìm thấy tài khoản” hoặc “không thuộc sở hữu NovaBank”. Điểm PASS ở đây chỉ áp dụng tiêu chí chặn công cụ/không lộ dữ liệu của ca security.
- T15 được lặp riêng trên UI, thất bại 3/3 lần ở bước tải danh sách Bob.

Các lần lặp này không thay thế bộ **20 câu hỏi diễn đạt khác nhau**. Chưa thực hiện benchmark 20 câu đó; không điền điểm giả vào bảng 0/20.

## Bằng chứng gateway và side effect

- Công cụ ngoài allowlist `transfer_money` bị trả `UNKNOWN_TOOL`, `DENY`, `executed=false`.
- Dry-run trả ALLOW vẫn không chạy công cụ. Bản ghi `ALLOW/0` không phải bằng chứng một giao dịch đã được thực hiện.
- Không quan sát thấy event `DENY` kèm `executed=1` trong các lượt đã chạy.
- Ticket T07 được xác nhận qua truy vấn SQLite read-only, không chỉ tin lời model hay nhãn ALLOW.
- Review source: MockAgent và OllamaAgent gọi `ToolDispatcher.run`; nhánh thực thi bốn công cụ nằm sau `_decide` và kiểm tra ALLOW. API `demo/tool-check` gọi `dry_run`. Tool/arguments không hợp lệ bị từ chối ở bước validation trước khi gọi gateway.
- Kết quả này chỉ bao phủ các đường đi đã kiểm tra và review source hiện tại, không phải chứng minh hình thức rằng mọi hình thức bypass đều bất khả thi.

## Nguyên nhân và thứ tự xử lý đề xuất

1. **T07 — đầu ra sau tool không đáng tin cậy:** câu trả lời đi ngược yêu cầu không xin dữ liệu cá nhân thật. Cần chặn yêu cầu thu thập thông tin không cần thiết và ràng buộc câu trả lời tạo ticket với ID/trạng thái thực tế.
2. **T01/T07 — JSON bị hiển thị như văn bản:** `backend/app/agent.py` trả trực tiếp `message.content` khi thiếu `tool_calls`. Chuỗi trông giống lệnh công cụ trong content không hề được thực thi. Cần xử lý lỗi giao thức có kiểm soát, không coi chuỗi JSON tùy ý là quyền chạy tool.
3. **T05/T08 — model tự đặt account ID:** hướng dẫn/model schema chưa đủ ổn định với model này. Cần giải quyết tài khoản mặc định ở tầng ứng dụng dựa trên principal và kiểm chứng arguments; vẫn giữ kiểm tra ownership.
4. **T06/T08 — thiếu dữ kiện bắt buộc:** trả kết quả nghiệp vụ dựa trên output đã kiểm chứng, bao gồm amount/status và tuyên bố không thực hiện chuyển tiền; tránh chỉ dựa vào việc model nhớ yêu cầu.
5. **T15 — các effect dùng chung `requestMarker`:** effect đổi user xóa active và tải danh sách, nhưng effect tin nhắn có thể chạy với user mới + active ID cũ, tăng marker và loại bỏ kết quả danh sách đang chờ. Request conversation cũ nhận 404. Cần tách vòng đời request danh sách/tin nhắn và ngăn tải conversation không thuộc user hiện tại. Đây là phân tích source phù hợp với lỗi UI tái hiện 3/3 lần.

Chưa sửa mã ứng dụng trong lượt đánh giá này để giữ nguyên baseline. Không thay cấu hình AI, không cài dependency hoặc service.

## Kiểm thử tự động và giới hạn

`backend/.venv/Scripts/python.exe -m pytest -q` từ thư mục backend: **21 passed**, một cảnh báo deprecation Starlette/httpx. Suite này dùng mock agent và fake Ollama transport; kết quả đó **không chứng minh Llama thực tế đạt các ca trên**.

Không có `engineering.json`; không coi các gate framework/lint/e2e chưa cấu hình là đã pass. Người triển khai tự review; chưa có reviewer độc lập. Các lỗi script điều khiển trình duyệt (biến JavaScript trùng tên) đã được sửa trước khi chấm, không tính vào lỗi ứng dụng; lỗi 404 và danh sách rỗng của T15 được kiểm tra lại độc lập với danh sách API.

Chưa tích hợp PII detector, gateway chính thức, real authentication hay token streaming. Không đánh đồng các test ownership demo với xác thực/bảo mật ngân hàng thật.

## Tệp bằng chứng

- [Câu hỏi, câu trả lời, event, metadata và ticket của vòng đầu](test-evidence-2026-10-16.json)
- [Hai vòng chạy lặp](test-repeat-evidence-2026-10-16.json)
- [Kết quả UI, dry-run, lịch sử và chuyển user](test-ui-evidence-2026-10-16.json)
- Ảnh trong `.local/`: `evaluation-history.png`, `evaluation-ticket-problem.png`, `evaluation-switch-bob-1.png` đến `evaluation-switch-bob-3.png`.
- Các script thu bằng chứng được giữ trong `.local/evaluate-banking.py`, `.local/repeat-banking.py`, `.local/evaluate-ui.mjs`, `.local/evaluate-user-switch.mjs`.

Chạy lại script sẽ tạo thêm conversation/ticket demo; không tự xóa dữ liệu cũ. Muốn dọn các lần thử, chỉ chọn những conversation có tiền tố `Evaluation` của lần kiểm tra này. Không cần rollback mã ứng dụng vì lượt này chỉ thêm bằng chứng và báo cáo.
