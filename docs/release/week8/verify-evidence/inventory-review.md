# Kiểm kê API và chất lượng bằng chứng

Nguồn ứng dụng là clone sạch ở `0548e998e44c9fb5400ae9211ffdaf6cdf677074`. Lấy route từ router của cả hai app, kiểm tra chéo từng operation với OpenAPI sau đó mới đối chiếu với tài liệu bên triển khai. DB tạo mới qua `scripts/seed_realistic.py --seed 20261115`. Request đi qua FastAPI TestClient tới đúng handler/middleware, dùng provider mock. Đợt này không kiểm tra kết nối TCP, reverse proxy hay Ollama. Agent có HTTP API riêng và ở mạng dịch vụ trong Compose. Cấu hình dev native có thể mở cổng local. Mount giao diện được bật bằng trang HTML tối thiểu trong thư mục tạm. Kiểm kê này kiểm tra quy tắc mount, không kiểm tra JavaScript build.

## Đọc kết quả

- [Ma trận đầy đủ](inventory-matrix.csv) có một dòng cho mỗi bộ service, method, path. Có 125 operation OpenAPI (Bank 123, Agent 2), 16 route framework GET/HEAD cho OpenAPI và tài liệu HTML, cùng một mount tùy chọn. Tổng cộng Bank có 132 dòng, Agent có 10.
- `roles` là vai trò chấp nhận ở tầng quyền của route. Giới hạn sở hữu tài nguyên, trạng thái giao dịch và xác thực bổ sung áp dụng bên trong handler. Quyền đọc từ dependency, ánh xạ quyền trong `backend/app/auth.py:46` và điều kiện trong handler. Ví dụ `GET /api/support/tickets` chặn riêng operations ở `backend/app/routes_support.py:48`. Dev inbox cần môi trường demo/review, route research cần bật sandbox và quyền admin. Route demo/tool-check chỉ có hành vi demo trong chế độ legacy test. Agent `POST /run` yêu cầu delegation do Bank xác thực ở `agent_service/main.py:199`.
- Mỗi `own_case` là ID của một kịch bản tái chạy trong `verify/mentor-inventory.py`. `historical_pass_cases` chỉ đếm bản ghi “passed” thật sự trong JSON cũ. Một dòng có trong registry nhưng chỉ có “not_applicable” không được tính là bằng chứng test đã qua.
- 142/142 dòng có tối thiểu phép thử method sai. OPTIONS không có Origin trả 405. Cùng một path có nhiều method chia sẻ phép thử 405. 112/112 route cần bearer/delegation trả 401 khi thiếu token. 111/111 route Bank cần token trả 401 với token sai đã thử. Agent /run được thử thiếu token. Nhánh xác thực token sai của Agent gọi ngược sang Bank, chưa được xác minh trong bộ TestClient tách rời. Không suy ra hành vi token đúng hoặc quá hạn từ ca token sai.
- GEN01 ghi rõ kiểm tra 200 và kiểu của một trường ở bảy operation, đồng thời tách các route framework/mount có test HTTP/MIME. Chưa chứng minh schema hoàn chỉnh cho 125 operation API. GEN04 chỉ chạy 15 GET sai vai trò, ghi rõ các ô bị thiếu. GEN05 dùng body rỗng ở chín biểu mẫu, chưa bao quát toàn bộ tổ hợp kiểu/độ dài/query. GEN06 rà dấu hiệu stack trace, SQL và đường dẫn nội bộ trong các response lỗi đã thu. Chưa gây lỗi 5xx hoặc kiểm tra toàn bộ cách tạo lỗi. Mọi cột được đánh dấu từng dòng.
- Bản thực thi cũ ở `docs/release/week8/api-observations.json` có 580 quan sát và 107 dòng service/method/path có tối thiểu một PASS. 107/125 (85,6%) là tỷ lệ operation có PASS trong **tệp lịch sử cụ thể này**. 107/142 (75,4%) dùng mẫu số gồm framework/mount. Cả hai đều là cận dưới của bằng chứng bên triển khai. Các bộ test khác có thể bao phủ thêm route. Smoke mới 142/142 không đủ để kết luận hợp đồng nghiệp vụ của mọi endpoint đã đạt.
- `docs/release/week8/API_TESTS.md:3` ghi 128 dòng. Bảng của tệp này thiếu toàn bộ 10 dòng Agent, cùng GET/POST `/api/documents` và GET/DELETE `/api/documents/{document_id}` của Bank. `backend/tests/route_matrix.json` hiện liệt kê 132 dòng Bank, bao gồm bốn document operation. `FUNC_API_TEST_REPORT.md:15` có DOC-API, nên không kết luận các route tài liệu chưa bao giờ được test. Digest registry hiện tại khác digest snapshot 580 quan sát. Danh sách thiếu chính xác từng service/method/path và cả hai digest nằm trong [kết quả đối chiếu](inventory-summary.json).

## Đánh giá bộ test bên triển khai

| ID | Kết quả | Bằng chứng trực tiếp |
|---|---|---|
| Q-1 | WEAK | `backend/tests/test_banking_core.py:31` đối chiếu hai dòng ledger, số tiền và audit. `backend/tests/test_documents_api.py:44` và `:58` kiểm tra trạng thái, preview, 404 sau khi xóa qua HTTP. Hai ca này không query trực tiếp để bắt trường hợp dữ liệu chunk vẫn nằm trong DB sau khi xóa mềm. Repository ẩn chunk khi tài liệu có deleted_at ở `backend/app/documents/repository.py:88`. |
| Q-2 | WEAK | `backend/tests/test_documents_api.py:58` có cặp 404 cho người khác và 200 cho chủ sở hữu. `backend/tests/test_documents_gateway.py:20` đối chiếu ALLOW/DENY. Tuy nhiên bảng trong `API_TESTS.md:7` không công bố ca dương đi kèm cho từng route và có nhiều hàng chỉ ghi từ chối hoặc N/A. Chưa xác nhận bao phủ toàn bộ suite. |
| Q-3 | FAIL | Assertion tại `backend/tests/test_customer_products.py:31` chấp nhận mọi HTTP status khác 200, kể cả 500. `backend/tests/test_layer_verification.py:346` cũng có thể đạt khi response là 500 và số dư giữ nguyên. Đây là kết luận đọc điều kiện trong mã. Các lượt chạy thực tế ở đây không ghi nhận server trả 500. |
| Q-4 | FAIL | `backend/tests/test_promptguard_local.py:8` tham số hóa hai model và `:12` gọi skip khi thiếu model được cấp phép. `backend/tests/test_outbox_takeover.py:19` đánh dấu strict xfail cho một lỗi đã sửa. Tìm trong backend/tests, research/tests, frontend/tests/e2e không thấy khai báo test bị comment theo mẫu def test_/test()/it(), skip hoặc xfail nào khác. Nhận xét mô tả xfail trong docstring không phải marker thực thi. |
| Q-5 | WEAK | Tự chạy mỗi lượt bảy ca bằng một lệnh pytest, dùng fixture DB tạm `backend/tests/conftest.py:50`. `scripts/document-rag-check.py:23` có runner tổng hợp và xuất XML/HTML, nhưng live/baseline cần cấu hình và artifact bổ sung ở dòng 46–70, mặc định ghi BLOCKED và trả mã 2 khi chỉ còn BLOCKED. Chưa xác nhận một lệnh kiểm tra toàn bộ phạm vi trong yêu cầu trên clone trống artifact. |
| Q-6 | WEAK | Cùng 7 node chạy liên tiếp, 7/7 mỗi lượt, không đổi verdict. Phạm vi ổn định xác nhận được là 7 test. Báo cáo gốc công bố backend + research lớn hơn phạm vi này. |
| Q-7 | PASS | Các lượt chạy mới xuất được [JUnit lượt 1](inventory-quality-1.xml) và [JUnit lượt 2](inventory-quality-2.xml). `scripts/document-rag-check.py:27` có cờ JUnit. XML/HTML gốc dẫn từ `.local` trong `FUNC_API_TEST_REPORT.md:70` không được track ở gói week8 của commit đã nghiệm thu. |

## Bằng chứng cho mục 1.5

| Mục | Kết quả | Vị trí và giới hạn |
|---|---|---|
| Bảng ID, endpoint, input, expected, actual, verdict | FAIL | `FUNC_API_TEST_REPORT.md:15` chỉ có ID, status và mô tả ngắn cho DOC-API; thiếu bảng tương đương cho mọi API và các cột expected/actual độc lập. |
| Độ phủ x/y của toàn hệ thống | FAIL | `FUNC_API_TEST_REPORT.md:30` nêu bốn endpoint tài liệu. Bảng 128 route cũ đã lệch mẫu số như trên; 94,17% ở dòng 58 là độ phủ dòng mã tài chính. |
| Failed attempts | PASS | `FUNC_API_TEST_REPORT.md:73`, `:163`, `:206` ghi nhận chất lượng bằng chứng, sửa oracle và rerun. Chưa độc lập lặp lại toàn bộ các sự cố đã ghi. |
| Số liệu khớp phép đo độc lập | WEAK | 128 route khớp số dòng trong API_TESTS.md lịch sử, 580 khớp số quan sát trong JSON. Mẫu số cho bản hiện hành và digest đã thay đổi. Số 1.024 test ở phiên bản cũ chưa được tái xác nhận trên toàn suite. |

## Tái chạy

Chọn clone sạch đúng SHA ghi trong JSON, dùng Python đã cài requirements backend và chạy tại workspace chứa verifier.

```powershell
rtk proxy backend\.venv\Scripts\python.exe verify/mentor-inventory.py <clean-checkout> docs/release/week8/verify-evidence
```

Tại thư mục clone sạch, chạy hai lần cùng danh sách node, thay `<python>` bằng đường dẫn tuyệt đối tới interpreter của venv và `<evidence>` bằng thư mục đích. XML ghi node ID và thời gian của từng ca. Các ca này kiểm tra code của người làm riêng với phép thử độc lập của ma trận.

```powershell
$cases = @(
  'backend/tests/test_banking_core.py::test_internal_posting_has_balanced_journal_and_one_audit'
  'backend/tests/test_banking_core.py::test_interbank_has_clearing_counterentry'
  'backend/tests/test_customer_products.py::test_savings_and_cards_use_balanced_posting'
  'backend/tests/test_documents_api.py::test_DOC_API_04_password_pdf'
  'backend/tests/test_document_review.py::test_summary_reads_the_short_document_in_order_without_a_query_embedding'
  'backend/tests/test_document_review.py::test_document_question_returns_the_isolated_answer_with_file_citations'
  'backend/tests/test_documents_api.py::test_DOC_API_02_authentication_before_body'
)
foreach ($round in 1,2) {
  rtk proxy '<python>' -m pytest -p no:cacheprovider -q --tb=line "--junitxml=<evidence>/inventory-quality-$round.xml" @cases
}
```
