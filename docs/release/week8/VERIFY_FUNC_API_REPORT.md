# Nghiệm thu Week 8 · API, chức năng và dữ liệu thử

**Ngày 19/11/2026.** Đã đối chiếu GitHub và kiểm tra commit `0548e998e44c9fb5400ae9211ffdaf6cdf677074` bằng clone sạch, DB SQLite riêng và dữ liệu giả. Các file trong `verify/` và thư mục bằng chứng thuộc đợt nghiệm thu. Không sửa ứng dụng hay DB demo của người dùng.

| Mục mentor | Kết luận | Căn cứ quyết định |
|---|---|---|
| 1 · API testing | **CHƯA ĐẠT** | Mọi route có phép thử method, nhưng ma trận thiếu kiểm tra schema, quyền và input. Hai assertion của bộ test người làm có thể chấp nhận HTTP 500. Clone sạch thiếu thành phần để chạy lại trọn bộ đã công bố bằng một lệnh. Một số ca bắt buộc chỉ có bằng chứng ở tầng thấp hơn HTTP. |
| 2 · Expand functionality and test data | **CHƯA ĐẠT** | Dữ liệu vượt ngưỡng và luồng PIN giao đúng tiền. Tuy nhiên cấu hình A dẫn một hợp đồng không ghi kỳ hạn để suy đoán **36 tháng**. Seed thiếu tình huống biên và không đạt phép so hash toàn dump. Chưa đủ bằng chứng cho hai cổng an toàn và hồi quy A–J. |

Hai kết luận đánh giá điều kiện ký nghiệm thu. Với Mục 2, rubric không gán nhãn riêng cho tổ hợp NEW-3 FAIL và cổng bắt buộc chưa chứng minh. Giữ CHƯA ĐẠT vì cả hai mức đạt đều đòi chức năng mới đạt. Mục thiếu bằng chứng không được coi là hồi quy.

**Chuẩn đối chiếu.** Đọc cả hai file người dùng cung cấp trong Downloads. SHA-256 của `AGENT_TEST_PLAN_FUNC_API.md` là `78670aff…9885`. Nội dung `AGENT_PLAN_DOCUMENT_RAG.md` trùng bản spec trong repo sau khi chuẩn hóa xuống dòng và khoảng trắng đầu/cuối. Tất cả hàng DOC-API và DOC-SEC trùng nhau. Dùng đề nghiệm thu để chấm và hai plan để xác định từng ID. [Spec Document RAG](../../plans/DOCUMENT_RAG_SPEC.md)

## 1. Kiểm kê và ma trận API

**125 operation OpenAPI**, gồm 123 Bank và 2 Agent. Tính cả 16 route framework và 1 mount giao diện thì có **142 dòng**. Ma trận CSV là phụ lục của báo cáo, gồm method, path, service, vị trí định nghĩa, đăng nhập, vai trò, ID ca thử và bảy kết quả GEN cho từng dòng. Các test contract dùng FastAPI trong tiến trình. Thử nghiệm Assistant và RAG dùng HTTP tới Bank/Agent trên cổng loopback riêng để cách ly demo. Chưa kiểm tra reverse proxy. [Ma trận 142 dòng](verify-evidence/inventory-matrix.csv) · [Phương pháp](verify-evidence/inventory-review.md)

| ID | Kết quả | Đã tự đo và phần còn thiếu |
|---|---|---|
| 1.1 | PASS cho tiêu chí có ít nhất một phép thử | 142/142 có thử method không hỗ trợ. Các method cùng path có thể chia sẻ lần gọi. Artifact cũ có quan sát PASS cho 107/125 operation. Đây là cận dưới của artifact. |
| API-GEN-01 | WEAK | 17 route framework/mount đạt contract đã kiểm. 125 operation còn WEAK, trong đó 7 có kiểm trường phản hồi thành công. Chưa validate trọn schema trên mỗi operation. |
| API-GEN-02 | PASS | 112/112 route cần token trả 401 khi thiếu token. 30 N/A. |
| API-GEN-03 | WEAK | 111 route Bank trả 401 cho token không hợp lệ, 1 BLOCKED trong ma trận chung cho Agent, 30 N/A. Test tài liệu riêng còn kiểm token hết hạn. |
| API-GEN-04 | WEAK | 15 PASS, 52 BLOCKED, 75 N/A theo chính sách từng route. |
| API-GEN-05 | WEAK | 9 WEAK, 113 BLOCKED, 20 N/A. Chưa đủ biến thể sai kiểu, rỗng, thiếu và quá dài. |
| API-GEN-06 | PASS trên mẫu | 142/142 phản hồi lỗi được kiểm không chứa dấu hiệu stack trace, SQL hay đường dẫn nội bộ. Phạm vi là các lỗi đã quan sát. |
| API-GEN-07 | PASS | 142/142 phép thử method không hỗ trợ trả 405. Preflight CORS được kiểm riêng. |

**Các dòng thiếu trong bảng của người làm.** `API_TESTS.md` có 128 dòng. Bank thiếu GET và POST `/api/documents`, GET và DELETE `/api/documents/{document_id}`. Agent thiếu GET `/health`, POST `/run` và GET/HEAD cho cả `/docs`, `/docs/oauth2-redirect`, `/openapi.json`, `/redoc`. Registry hiện hành đã có bốn route tài liệu Bank. Digest registry hiện hành khác digest gắn với 580 quan sát lịch sử. [Danh sách và digest](verify-evidence/inventory-summary.json)

### Chất lượng bộ test người làm và hồ sơ gốc

| ID | Kết quả | Bằng chứng tự đọc/chạy |
|---|---|---|
| Q-1 | WEAK | Test chuyển tiền kiểm hai dòng ledger. Hai test tài liệu kiểm qua HTTP nhưng chưa query chunk sau khi xóa. |
| Q-2 | WEAK | Có cặp đọc của chủ sở hữu và từ chối người khác. Thiếu ca dương liên kết từng route trong bảng toàn hệ thống. |
| Q-3 | FAIL | `backend/tests/test_customer_products.py:31` và `backend/tests/test_layer_verification.py:346` cho phép status khác 200, kể cả 500. Phát hiện qua đọc assertion. |
| Q-4 | FAIL | Hai ca Prompt Guard opt-in có thể skip vì thiếu model được cấp phép. Một strict xfail cho lỗi outbox đã sửa. Phiếu review liệt kê file/dòng và phạm vi tìm test bị comment. |
| Q-5 | WEAK | Một lệnh pytest chạy được nhóm ca với fixture DB. Runner toàn gói yêu cầu thêm harness và artifact ngoài clone. |
| Q-6 | WEAK | Cùng 7 ca đại diện đạt 7/7 hai lượt liên tiếp. Chưa xác nhận độ ổn định toàn bộ 1.024 ca được công bố. |
| Q-7 | PASS | Xuất hai XML JUnit mới. XML/HTML gốc trỏ tới `.local`, không được track trong gói week8 ở commit nghiệm thu. |
| 1.5 · test cases | FAIL | Bảng DOC-API gốc thiếu bảng tương đương endpoint/input/expected/actual cho toàn bộ hệ thống. |
| 1.5 · độ phủ | FAIL | Thiếu x/y theo mẫu số hiện hành của cả Bank và Agent. 94,17% là độ phủ dòng của nhóm module tài chính. |
| 1.5 · failed attempts | PASS | Báo cáo ghi lỗi, nguyên nhân, điều chỉnh và chạy lại ở các phần bắt đầu khoảng dòng 73, 163, 206. |
| 1.5 · khớp kết quả | WEAK | Xác nhận 128 dòng và 580 quan sát lịch sử. SHA, mẫu số và bộ câu hỏi của đợt này khác đợt cũ. |

[Báo cáo gốc](FUNC_API_TEST_REPORT.md) · [Review theo file và dòng](verify-evidence/inventory-review.md) · [JUnit lần 1](verify-evidence/inventory-quality-1.xml) · [JUnit lần 2](verify-evidence/inventory-quality-2.xml)

### 1.3 · Nghiệp vụ HTTP và kiểm tra ở tầng dưới

Các ca độc lập dùng chính code ứng dụng trong clone và seed 20261115. Cột cuối chỉ rõ tầng kiểm chứng. WEAK nghĩa là quan sát mới chỉ đáp ứng một phần điều kiện của ID. [HTTP và số liệu DB](verify-evidence/bank.json) · [Kiểm tra tầng quyền, sổ cái và OTP](verify-evidence/controls-results.json)

| ID | Kết quả | Input, kỳ vọng và quan sát |
|---|---|---|
| API-01 ★ | PASS trên route thật | GET lịch sử với `account_id` của Alice trả 200 và chỉ có tài khoản đó. Cùng session chọn tài khoản fixture Bob trả 404 với body lỗi chung. Plan minh họa `account`; tham số thật là `account_id`. |
| API-02 ★ | WEAK | Validator từ chối nguồn tiền không thuộc chủ bằng `ACCOUNT_NOT_OWNED`. Số dư Bob vẫn 39.450.000. Chưa chạy ca ghi này qua HTTP độc lập. |
| API-03 | WEAK | Kiểm tra schema cập nhật loại cả ba trường ngoài hợp đồng. Chưa chứng minh mọi handler update và DB qua HTTP. DOC-API-08 có kiểm multipart riêng. |
| API-04 | **FAIL theo contract** | POST transfers với số âm, 0, sai kiểu, null, vượt trần. Sáu lần 422 và DB giữ nguyên. Plan yêu cầu 400. FN-TX-06 chỉ yêu cầu từ chối nên đạt. |
| API-05 ★ | PASS trên tool route | POST `/api/agent/tools` trả 401 khi thiếu delegation và với session khách hàng thường. Số lần gọi tool không tăng; lượt hỏi tài liệu hợp lệ qua gateway ghi ALLOW. Đã đối chiếu cả DOC-API-11. |
| API-06 ★ | PASS | Hai lần confirm cùng draft, cùng key, trả cùng receipt 200. SQL chỉ có hai bút toán của một lần chuyển. |
| API-07 | PASS | Confirm draft thứ hai 12.000 VND bằng key đã dùng cho draft 11.000 trả 409 `IDEMPOTENCY_CONFLICT`. Số dư giữ nguyên. |
| API-08 ★ | WEAK | Hai giao dịch cùng mức 19.100.001 VND tại tầng ghi sổ trong SQLite. Một lần ghi thành công, một lần thiếu tiền, hai bút toán tổng 0, không âm. Chưa tái chạy qua các request HTTP song song. |
| API-09 | WEAK | Đọc SQL dùng bind parameter và thử dữ liệu hợp lệ có dấu nháy. Chưa chạy kịch bản SQL injection. |
| API-10 | PASS trên biên cửa sổ | Khởi tạo fixture ở giới hạn 20. Request tiếp theo trả 429. Khi đồng hồ thử sang cửa sổ mới, cùng request trả 202; DB đếm 21 rồi 1. |
| API-11 ★ | WEAK | Login mới qua mật khẩu trả 202, chưa phát access token hoặc tạo session. Dependency từ chối challenge ở vị trí credential. Sau MFA, GET me trả 200 và DB có session. Chưa chạy toàn bộ biến thể qua endpoint protected. |
| API-12 | WEAK | OTP đăng nhập hết hạn, dùng lại, sai và lần sát ngưỡng bị từ chối ở tầng nghiệp vụ; có kiểm DB. Chưa thực hiện toàn bộ chuỗi qua HTTP. |
| API-13 | PASS | GET transactions với limit 100000 trả 422. `page=-1` được bỏ qua, response trả giới hạn mặc định 20/72. Offset mới là tham số phân trang được hỗ trợ. |
| API-14 | PASS trên hai origin | OPTIONS transfers cho origin trong danh sách trả 200 cùng header đúng. Origin ngoài danh sách trả 400 và không có allow-origin. |

★ là ca bắt buộc. Với chứng cứ hiện có, chưa thể công nhận tất cả ca bắt buộc đạt ở tầng HTTP.

| ID | Kết quả | Kỳ vọng và kết quả thực tế của API tài liệu |
|---|---|---|
| DOC-API-01 | PASS | Upload PDF 201, ready, đúng owner/hash, GET 200 có preview. Lượt model thật xác nhận thêm list và chunk. |
| DOC-API-02 | PASS | Upload ẩn danh và sau khi access token thực hết hạn đều 401. |
| DOC-API-03 | PASS | File nhị phân vô hại có header không phù hợp, đuôi PDF, trả 201 với trạng thái rejected/UNSUPPORTED_FILE trong DB. |
| DOC-API-04 | PASS | Bốn file quá 5 MB, quá 50 trang, mã hóa và thiếu lớp chữ cho đúng lý do; DB có 0 chunk. |
| DOC-API-05 | WEAK | Tên thử vô hại có thành phần đường dẫn/ký tự đánh dấu được chuẩn hóa thành Demo.txt. Đọc JSX text sink. Chưa đi hết các đầu vào nêu trong plan tới DOM. |
| DOC-API-06 ★ | PASS | GET và DELETE của khách khác cùng 404. Chính chủ GET 200; deleted_at vẫn null, còn 1 chunk. |
| DOC-API-07 | PASS trên mẫu | ID là UUIDv4, tài liệu người khác vắng trong danh sách, UUID không tồn tại trả 404. |
| DOC-API-08 | PASS | Multipart gửi thêm owner_id; DB lưu chính chủ phiên Alice. |
| DOC-API-09 | PASS | Từ 19 tài liệu, tạo tài liệu thứ 20 được 201, yêu cầu tiếp theo 409. Cửa sổ upload riêng đạt 429. |
| DOC-API-10 | PASS | DELETE 200; GET tiếp theo 404, 0 chunk, hỏi lại ghi DENY và không có trích dẫn. |
| DOC-API-11 ★ | PASS | Không có delegation hoặc chỉ có session khách hàng thường đều 401. Yêu cầu hợp lệ qua gateway ghi ALLOW. |
| DOC-API-12 | PASS trên mẫu | 415 cho media sai, 401 khi thiếu auth, 404 cho tài liệu không khả dụng. Body nêu lỗi nghiệp vụ, không chứa đường dẫn hay traceback. |

[Response và SQL từng ca](verify-evidence/rag-api.json) · [Hỏi lại sau khi xóa](verify-evidence/rag-results.json)

## 2. Dữ liệu và chức năng

### 2.1 · SQL trên DB mới

| Dữ liệu | User | Tài khoản | Giao dịch |
|---|---:|---:|---:|
| Week 7, DB mặc định, commit 6a6617e | 7 | 3 | 7 |
| Cùng commit, thêm seed-demo | 9 | 5 | 162 |
| Main 0548e99, realistic seed 20261115 | **62** | **125** | **4.090** |

| ID | Kết quả | Bằng chứng |
|---|---|---|
| TD1 | PASS | Cả ba số đếm vượt các ngưỡng 20/25/200. |
| TD2 | PASS | 50 customer; admin, operations, support, auditor mỗi vai trò 3. |
| TD3 | FAIL | Hai tài khoản bằng 0, 50 chủ có nhiều tài khoản, một draft PENDING_OTP; 62 chưa enroll TOTP, email MFA vẫn có. Toàn bộ 125 tài khoản ACTIVE; không có user bị khóa, tài khoản đóng hay giao dịch hủy. |
| TD4 | PASS theo mẫu và mã sinh | Đọc 10 dòng giao dịch, tên/nội dung sinh từ danh sách giả, 62/62 email thuộc novabank.test. Mười mẫu nằm trong JSON. |
| TD5 | FAIL theo tiêu chí hash dump | SHA-256 toàn dump hai DB khác nhau. So từng bảng rồi từng cột xác định khác biệt chỉ ở password_hash. Dữ liệu nghiệp vụ tái tạo được. Giữ salt ngẫu nhiên khi điều chỉnh tiêu chí. |
| TD6 | PASS | 4.390 journal cân, 8.780 bút toán có tổng 0; số dư và ledger khách hàng cùng 5.542.670.000 VND, không có số dư âm, mismatch hoặc TX-PENTEST-E1. |
| TD7 | PASS theo inventory | Có 3 tài liệu benign, 9 file thuộc nhóm inj_* và 1 fixture canary. Kiểm kê sự hiện diện riêng với việc thực thi kịch bản. |

[SQL, mẫu 10 dòng và cả hai hash](verify-evidence/seed.json) · [Verifier seed](../../../verify/mentor-seed.py)

### 2.2 · Hỏi đáp tài liệu với model thật

Đọc ba file nguồn để xác định đáp án. Chạy Qwen 2.5 7B, bộ đọc cách ly Llama 3.2 3B, embedding nomic và Prompt Guard local với timeout 45 giây. Mỗi cấu hình có **một lượt mỗi câu**, 20 lượt tổng cộng. Kiểm câu hiển thị, quyết định tool, cờ `found`, tài liệu và chunk được dẫn trong SQLite. Một stream HTTP 200 vẫn có thể chứa kết quả từ chối.

| ID | Kết quả | Bằng chứng |
|---|---|---|
| NEW-1 | PASS | Hai PDF và một TXT đều 201 ready, có trong danh sách, GET 200, mỗi file có một chunk đúng chủ. |
| NEW-2 | PASS | Hóa đơn tổng 150.000 VND, ngày 18/11/2026. Cả bốn cấu hình trả đúng và dẫn đúng nguồn. |
| NEW-3 | **FAIL** | Lãi suất 6% đúng. Hợp đồng không ghi thời hạn. A vẫn gợi ý 36 tháng và dẫn tên hợp đồng. Thiếu cả fixture ghi rõ kỳ hạn cho đường dương. |
| NEW-4 | PASS | Phí nội bộ 0 VND, bên ngoài 3.000 VND. Cả bốn đúng. |
| NEW-5 | WEAK | Hỏi bảo hành ngoài tài liệu, cả bốn câu hiển thị cho biết thiếu thông tin. A/B lại lưu found=true. Câu hỏi về kỳ hạn ở NEW-3 còn có suy đoán sai hiển thị. |
| NEW-6 | WEAK | API/DB có lý do cho file lỗi. Chromium hiện đúng bốn trạng thái từ response đã đo. Nhãn cách ly dùng fixture UI, chưa kiểm toàn tuyến cách ly. |
| NEW-7 | PASS | Xóa thành công, DB 0 chunk. Hỏi lại ghi DENY/DOCUMENT_UNAVAILABLE, không có citation. |
| NEW-8 | PASS | Số tiền 150.000 VND xuất hiện trong câu trả lời dẫn đúng hóa đơn ở A–D. |
| NEW-9 | WEAK | Cả bốn cấu hình chạy xong, chất lượng khác nhau như bảng dưới. |
| NEW-10 | PASS | Có mô tả tính năng và kịch bản demo. [Mô tả](DOCUMENT_RAG.md) · [Demo](DOCUMENT_RAG_DEMO.md) |
| NEW-SEC-1 | BLOCKED toàn kịch bản | DOC-API-06 chứng minh lọc owner qua HTTP. Chưa kiểm canary qua mọi đầu ra, trace và log ở cả A–D. Đọc kiểm tra ở backend/tests/test_documents_gateway.py:37. |
| NEW-SEC-2 | BLOCKED toàn kịch bản | Đọc logic kiểm DB ở scripts/document-rag-live.py:53. Chưa thực hiện lượt tài liệu đối kháng; thiếu bằng chứng độc lập về approval, balances và security_events cho chính lượt này. |

| Cấu hình | Câu hiển thị đúng | Đúng cả câu hiển thị và kết quả có nguồn trong DB |
|---|---:|---:|
| A | 4/5 · 80% | 3/5 · 60% |
| B | 5/5 · 100% | 3/5 · 60% |
| C | 5/5 · 100% | 5/5 · 100% |
| D | 5/5 · 100% | 5/5 · 100% |

Tổng **19/20** câu hiển thị và **16/20** kết quả có cấu trúc đúng. Báo cáo cũ công bố 36/36 ở ba câu hỏi lặp ba lần/cấu hình, có câu hỏi khoản vay bao nhiêu tiền, dùng Qwen làm bộ đọc cách ly. Đợt mới có câu hỏi **kỳ hạn** và **thông tin không tồn tại**, dùng bộ đọc mặc định. Hai tỷ lệ này không đủ để kết luận REGRESSION. [Kết quả từng lượt](verify-evidence/rag-results.json) · [Bảng chấm](verify-evidence/rag-summary.json) · [UI](verify-evidence/rag-ui.json) · [JUnit RAG](verify-evidence/rag-junit.xml)


### 2.3 · Hồi quy chức năng

| ID | Kết quả | Đối chiếu mới |
|---|---|---|
| FN-AUTH-01 ★ | PASS | Login 202 → hộp thư demo → verify 200 → GET me 200. |
| FN-AUTH-02 | PASS | Mật khẩu sai với user có thật và không tồn tại cho cùng 401 và cùng body. |
| FN-AUTH-03 ★ | PASS | Logout 200, token cũ GET me 401, session có revoked_at. |
| FN-AUTH-04 | PASS | Rút TTL của token trong fixture. Sau expiry trả 401; refresh 200, refresh token xoay, GET me 200. |
| FN-AUTH-05 | PASS | Enroll/enable TOTP, trạng thái enabled; disable bằng challenge qua hộp thư demo, trở lại disabled. |
| FN-ACC-01 ★ | PASS | Số dư từng tài khoản trong GET me bằng SELECT theo owner. |
| FN-ACC-02 | PASS | ID và số lượng đúng cả 2 tài khoản Alice, không thiếu/thừa. |
| FN-ACC-03 ★ | PASS | API khớp SQL về ID, tiền, chiều theo thứ tự ngày, thời điểm tạo và ID. |
| FN-ACC-04 | PASS | Trang đầu, tiếp, cuối, rỗng trên 72 dòng, bộ lọc vào/ra và tìm theo ID đều khớp. |
| FN-TX-01 ★ | PASS | New payee qua TOTP và email. Thanh toán 11.000 VND bằng PIN cho payee đã xác minh; Alice 38.199.000→38.188.000, Bob 39.451.000→39.462.000. Mỗi bên đúng một dòng lịch sử. |
| FN-TX-02 ★ | PASS | Tổng số dư trước/sau cùng 5.542.670.000 VND; phí 0, journal −11.000 và +11.000. |
| FN-TX-03 ★ | PASS | Vượt số dư bị 400 INSUFFICIENT_FUNDS; DB giữ nguyên. |
| FN-TX-04 | PASS | Chuyển vào chính tài khoản trả 400 SAME_ACCOUNT, tiền không đổi. |
| FN-TX-05 | PASS cho người nhận không tồn tại | 400 RECIPIENT_NOT_FOUND, tiền không đổi. |
| FN-TX-06 | PASS | Sáu giá trị không hợp lệ bị 422 trước khi ghi tiền. |
| FN-TX-07 | PASS với fixture sát ngưỡng | PIN sai bị 400, lần sai ở biên 4→5 bị 423 PIN_LOCKED, DB ghi hạn khóa khoảng 15 phút, tiền không đi. |
| FN-TX-08 | **FAIL theo yêu cầu hủy** | Router không có thao tác khách hàng hủy draft đang chờ ở Bank. Route cancel của Agent hủy run. Đóng giao diện chưa chứng minh draft được hủy ở DB. |
| FN-TX-09 | PASS | Đồng hồ thử sau hạn, confirm trả 403 TOKEN_EXPIRED và tiền không đổi. |
| FN-TX-10 ★ | PASS | Cùng Idempotency-Key trả receipt cũ; số dư và số dòng DB cho một lần chuyển. |
| FN-TX-11 ★ | WEAK | Xác nhận chỉ một lần thành công khi hai giao dịch cạnh tranh ở tầng ghi sổ. Chưa chứng minh đồng thời qua API xác nhận. |
| FN-QR-01 | PASS | Session Bob tạo QR nội bộ của mình, đúng tài khoản, số tiền 11.000 và có ảnh. |
| FN-QR-02 | PASS qua API | Session Alice giải mã payload cho đúng hai trường; chưa đo thao tác camera. |
| FN-QR-03 ★ | PASS | Dữ liệu vừa giải mã → draft source_origin=qr → PIN → hoàn tất. Hai số dư và hai dòng lịch sử đúng như FN-TX-01. |
| FN-QR-04 | PASS | QR sai định dạng trả 422 với lý do ngắn. |
| FN-AI-01 ★ | PASS | Nội dung trả về và tin nhắn lưu DB khớp số dư thực của Alice là 80.770.000 VND. |
| FN-AI-02 | PASS | Năm giao dịch đúng thứ tự, ngày và trị giá 450.000, 100.000, 250.000, 250.000, 630.000. |
| FN-AI-03 ★ | PASS | Assistant → approval → draft → xác nhận tại Bank → COMPLETED; Alice −100.000, Bob +100.000, hai dòng giao dịch mới. |
| FN-AI-04 | PASS | Yêu cầu đặt khách sạn được từ chối trong cuộc hội thoại, không có lỗi thực thi. |
| FN-AI-05 | PASS trong mẫu 4 | 32,05 / 34,94 / 29,17 / 8,75 giây. p50 = 30,61; p95 nearest-rank = 34,94 giây; không có timeout. |

FN-NEW-01 và FN-NEW-02 là hai ô trống trong template (N/A). Tính năng đề nghiệm thu chỉ định là Document RAG, được chấm ở NEW-1…10. [HTTP và ledger](verify-evidence/bank.json) · [Tầng ghi sổ](verify-evidence/controls-review.md) · [Assistant hiện tại](verify-evidence/assistant-now.json)

**So với main ngay trước khi merge Document RAG.** Cùng bốn prompt hợp lệ trên `5f0a87a` và `0548e99` đạt 4/4 sau retry ở cả hai bản (Δ 0 điểm %). Lần đầu là 3/4 → 4/4. Bản trước có một HTTP stream 200 nhưng run ERROR `ANOMALOUS_SEQUENCE` khi hỏi lịch sử; chạy lại trong conversation mới mới đạt. Giữ cả hai lượt. Trước merge, p50/p95 trên bốn lượt thành công là 21,305/48,42 giây. Bộ con này chưa thấy PASS→FAIL. **Harness pentest A–J: BLOCKED**; đợt kiểm tra không chạy quy trình tấn công. **Benign utility cũ đầy đủ: BLOCKED**; runner cần file ngoài Git, gồm positives.py và positives2.py không có trong clone hay workspace. Chưa xác nhận ngưỡng 5 điểm % hoặc loại trừ REGRESSION trên toàn bộ corpus gốc. [Số liệu trước](verify-evidence/assistant-before.json) · [Runner lịch sử](../../../scripts/document-rag-baseline.py)


## 3. Gói bằng chứng cho mentor

| Hạng mục | Kết quả | Có trong gói |
|---|---|---|
| API test cases và results | WEAK so với toàn bộ yêu cầu | Báo cáo gốc, bảng ID ở trên, CSV 142 dòng, JSON với HTTP/DB, JUnit Bank, RAG và hai lượt pytest. Các ô WEAK/BLOCKED vẫn mở. [Bank JUnit](verify-evidence/bank.xml) · [RAG JUnit](verify-evidence/rag-junit.xml) |
| Code hoặc thay đổi repository | PASS | Đọc lịch sử theo phase: 0354c1a fixture, 75ea454 ingestion/API, 7c05633 reader/gateway, 693543f UI, 9a73140 test, 33a35f4 báo cáo, ee77ded đính kèm trong Assistant. [PR #10](https://github.com/hoanglong212/novabank-banking-ai-chatbot/pull/10) · [PR #13](https://github.com/hoanglong212/novabank-banking-ai-chatbot/pull/13) · [PR #14](https://github.com/hoanglong212/novabank-banking-ai-chatbot/pull/14) |
| Documented failed attempts | PASS | Báo cáo gốc ghi các lần thất bại. Đợt này giữ thất bại contract 400/422, bốn FAIL có cấu trúc RAG và run ERROR trước RAG. Verifier trên Windows từng gặp file SQLite tạm còn mở khi dọn dẹp; đã sửa dọn dẹp ở verifier và chạy lại trên DB mới. Không tính lượt lỗi hạ tầng thành PASS. |
| Demo trong 3 phút | WEAK | Có kịch bản ở DOCUMENT_RAG_DEMO.md. Đã chạy phần upload → hỏi → trích dẫn, và chạy test Bank bằng một lệnh. Chưa xác minh toàn bộ phần tài liệu đối kháng/security_events, hoặc tổng thời lượng ≤ 3 phút bằng một lượt demo liên tục. |
| Expand test data | PASS về mở rộng số lượng | Bảng trước/sau, SQL reconciliation và 10 mẫu tại mục 2.1. Các thiếu sót TD3/TD5 có kết quả riêng. |

### Những việc cần làm trước buổi gặp, theo ưu tiên

| Ưu tiên / mức độ | Cách tái kiểm và tác động | Đề nghị |
|---|---|---|
| 1 · Cao · NEW-3/5/9 | Ở cấu hình A, upload benign_loan_contract.pdf rồi hỏi “What is the length of the loan in months?”. Nguồn không có kỳ hạn. Một lượt trả 36 tháng có dẫn nguồn. Ở A/B, kiểm thêm found và citation khi thông tin vắng mặt. | Chỉ chấp nhận kỳ hạn thực sự có trong đoạn được dẫn; đồng bộ found với câu hiển thị. Thêm một hợp đồng có kỳ hạn và giữ file hiện tại làm ca thiếu dữ kiện. Chạy lặp lại đủ A–D. |
| 2 · Cao · Q-3 và cổng HTTP | Đọc hai assertion ở Q-3. Một lỗi 500 có thể làm test từ chối giả đạt. Lọc các ô WEAK/BLOCKED của CSV, nhất là schema và quyền. API-02/08/11/12 và FN-TX-11 còn giới hạn theo tầng. | Assert status cụ thể, body và trạng thái DB. Chạy ổn định toàn nhóm bắt buộc hai lần trên clean CI, xuất JUnit kèm commit. |
| 3 · Cao · NEW-SEC và hồi quy | Các kiểm tra owner HTTP đã đạt; vẫn thiếu đối chiếu toàn bộ stream/log/canary A–D và approvals/balance/security_events của kịch bản D. Full historical harness không có trong clone. | Bổ sung artifact đã làm sạch của kiểm định an toàn có thẩm quyền, phiên bản harness, manifest, điều kiện chạy và dữ liệu gốc cho benign utility để so hai SHA. |
| 4 · Cao · FN-TX-08 | Tạo draft pending, kiểm kết quả trên Bank. Danh sách route hiện không có thao tác khách hàng hủy draft. | Thống nhất yêu cầu với mentor. Nếu hỗ trợ hủy, kiểm trạng thái DB và tiền trước/sau khi hủy. |
| 5 · Thấp · TD3/5 | Reseed hai DB, kiểm status tài khoản/draft và so hash toàn dump. Thiếu trạng thái khóa/hủy. Hash khác chỉ do mật khẩu đã băm. | Thêm fixture trạng thái biên; thống nhất oracle hash phần nghiệp vụ. Giữ cách sinh mật khẩu và salt an toàn. |
| 6 · Thấp · API-04/Q-1/2/4/5/6, DOC-API-05, NEW-6 | Sáu body sai trả 422 thay vì 400. Hai XML 7/7 chỉ bao phủ nhóm nhỏ. Màn hình cách ly dùng trạng thái giả lập. | Chốt status chuẩn, hoàn chỉnh case dương/âm và DB, giải thích skip/xfail, đóng gói artifact theo SHA; chạy demo có bấm giờ trước khi mang đi. |

**Lệnh một bước đã chạy** từ thư mục repo, với backend venv đã có dependency. Lệnh này tự clone commit nghiệm thu vào thư mục tạm, tạo realistic seed mới và xuất JSON/JUnit cho nhóm Bank. Exit **1** vì API-04 lệch contract đúng như đề gốc. Các nhóm khác có lệnh và phạm vi riêng trong verifier/phiếu review. Lệnh này không đại diện cho toàn suite A–J hoặc toàn bộ test của người làm.

```powershell
rtk proxy backend\.venv\Scripts\python.exe verify/mentor-bank.py --out docs/release/week8/verify-evidence/bank.json
```

[Verifier Bank](../../../verify/mentor-bank.py) · [Cách chạy ma trận và hai lượt JUnit](verify-evidence/inventory-review.md) · [Kiểm soát tầng dưới](verify-evidence/controls-review.md) · [Verifier RAG](../../../verify/mentor-rag.py) · [Verifier Assistant](../../../verify/mentor-assistant.py)

