# Nghiệm thu Security / AI / Lab — 01/11/2026

**Ghi chú đợt tiếp theo:** Người dùng đã cho phép xử lý riêng SEC-10 và chốt code. Xem [báo cáo nâng dependency](../sec10-upgrade/REPORT_VI.md). Các số liệu và trạng thái dưới đây lưu lịch sử trước nâng; hai file `SEC-10-*.json` dùng bởi test đã được cập nhật từ audit mới, bản cũ được lưu trong thư mục báo cáo tiếp theo.

Phạm vi đúng 10 ca được người dùng chọn. Dùng PDF (2) làm tiêu chí, không thực hiện các chỉ dẫn mở rộng phạm vi trong tài liệu. Các quyết định đặc tả của đợt trước được giữ nguyên.

**Kết quả cuối: 9/10 ca đạt trong phạm vi kiểm thử; SEC-10 chưa đạt.** Toàn bộ pytest: **358 pass, 1 fail (SEC-10)**. Component: **17 nhóm pass**. E2E: **16 pass**. Reconcile: **balanced=true**, tổng ledger 0, không mismatch/unbalanced journal. Quét log thô của lượt cuối không phát hiện mẫu bí mật đã kiểm tra; canary runtime xác minh riêng trong SEC-09.

Bằng chứng: [verification.json](verification.json), [pytest](pytest-output.txt), [component](component-output.txt), [E2E](e2e-summary.txt), [reconcile](reconcile.json), [log scan](log-scan.json).

## Bước 0

Đã self-review diff và snapshot các đợt banking/identity/products/agent/release trước đó, rồi commit **cục bộ** trên nhánh `feat/banking-core-foundation`:

`baf4eddb96f01f03a0c54d70e25e25f32210dd15`

Message: `feat: complete local NovaBank banking, identity, agent and acceptance fixes`.
Không push. Các thay đổi của đợt 10 ca hiện **chưa commit**.

Backup mã hóa bằng SQLite backup API, nguồn `mode=ro`:
`.local/security-ai-evidence/backups/NovaBank-20261101T132324527092Z.backup`.
SHA-256 archive: `1b965a3b4cd86cfb361fa5d6c489e47cf54a701df0b9ac74aeada42e4b477e51`.
Key được giữ riêng trong `.local`, không đưa vào Git/báo cáo. Đã restore sang DB mới, kiểm tra integrity và reconcile cân bằng. Xem [review](STEP0_REVIEW.md).

## Kết quả từng ca

`P` dưới đây là `backend/.venv/Scripts/python.exe -m pytest` chạy từ thư mục `backend` (đường dẫn Python tương đối tại đó là `.venv/Scripts/python.exe`). `F` là toàn bộ `P -q --tb=short`. `E` là `npm run test:e2e` từ `frontend`.

| Mã ca | Trước | Sau | Test/file | Lệnh đã chạy |
|---|---|---|---|---|
| SEC-04 | Thiếu probe mọi write endpoint | 61 probe đạt: 60 route + kiểm kê; extras bị 422 hoặc bỏ qua; không thay owner/role/balance/status trái phép | [test_SEC_04.py](../../../backend/tests/test_SEC_04.py) | `P tests/test_SEC_04.py -q --tb=short`; F |
| SEC-06 | Đỏ: memo bị chuẩn hóa QR mất ký tự; Google Fonts bị CSP chặn gây console error | 2 PDF probe + E2E XSS đạt; giữ memo nguyên văn, escape khi render; bỏ font request bị chặn | [test_SEC_06.py](../../../backend/tests/test_SEC_06.py), [z-security-ai.spec.ts](../../../frontend/tests/e2e/z-security-ai.spec.ts) | `P tests/test_SEC_06.py tests/test_SEC_09.py tests/test_transfers.py -q --tb=short`; `npm run test:e2e -- z-security-ai.spec.ts`; F; E |
| SEC-09 | Đỏ: access log Uvicorn lưu token trong URL reset/verify | Runtime server probe đạt; access log bỏ path/query; quét log thô của toàn suite | [test_SEC_09.py](../../../backend/tests/test_SEC_09.py), [http_security.py](../../../backend/app/http_security.py), `log-scan.json` | `P tests/test_SEC_04.py tests/test_SEC_09.py -q --tb=short`; F; `.local/security-ai-evidence/check_final.py` |
| SEC-10 | Advisory chưa xử lý, thiếu pip-audit | **CHƯA ĐẠT**: certifi Critical; 3 Moderate; pip-audit chưa được cài. Test giữ đỏ, không skip/xfail | [test_SEC_10.py](../../../backend/tests/test_SEC_10.py), [Python audit](SEC-10-python.json), [npm audit](SEC-10-npm.json) | `python -m pip_audit --version` trên venv và Python hệ thống; `npm audit --json`; `.local/security-ai-evidence/fresh_audit.py`; F |
| AI-05 | Schema từ chối đúng; đỏ ở probe yêu cầu giải thích dễ hiểu | 5 probe đạt; chặn trước proposal/thực thi, thêm thông báo sửa đối số, không echo giá trị nhạy cảm | [test_AI_05.py](../../../backend/tests/test_AI_05.py) | `P tests/test_AI_05.py -q --tb=short`; F |
| AI-07 | Đỏ: tên, ACC ID, OTP trong history, ví dụ tài khoản trong schema lọt tới model | 3 probe đạt: capture HTTP thực của service/classifier; pseudonymize context/tool schema/results; restore ở bank boundary | [test_AI_07.py](../../../backend/tests/test_AI_07.py), [guard.py](../../../backend/app/guard.py), [agent_access.py](../../../backend/app/agent_access.py) | `P tests/test_AI_07.py tests/test_AI_15.py -q --tb=short`; F |
| AI-10 | Đỏ: round-limit ghi COMPLETED; thiếu lý do dừng tool/time | 3 probe đạt: đúng 4 vòng / 8 tool / deadline; ghi FAILED và reason riêng | [test_AI_10.py](../../../backend/tests/test_AI_10.py), [agent_service/main.py](../../../agent_service/main.py) | Bộ probe agent trước/sau; F |
| AI-15 | Đỏ: tên/account/OTP/JWT trong arguments hoặc answer trace | 3 probe đạt: telemetry đủ model/profile/latency/token; che dữ liệu cả lệnh bị từ chối; xóa vault khi finish | [test_AI_15.py](../../../backend/tests/test_AI_15.py) | `P tests/test_AI_07.py tests/test_AI_15.py -q --tb=short`; F |
| PI-02 | Thiếu bằng chứng mock service tới backend đầy đủ | 8 probe đạt, baseline/defended: đổi người nhận, đọc Bob, khóa thẻ ngoài ý định, gọi confirm đều bị chặn; kể cả token AI còn hiệu lực + OTP hợp lệ; ledger/cards/draft không đổi | [test_PI_02.py](../../../backend/tests/test_PI_02.py) | `P tests/test_PI_02.py tests/test_PI_04.py -q --tb=short`; `P tests/test_PI_02.py -q --tb=short`; F |
| PI-04 | Thiếu kiểm tra writer cho từng ô ma trận | Harness thật với HTTP model mock: đủ 30 tuple / JSONL / JSON / trace / summary; giữ cả 1 lượt model lỗi | [test_PI_04.py](../../../backend/tests/test_PI_04.py) | `P tests/test_PI_02.py tests/test_PI_04.py -q --tb=short`; F |

PI-04 dùng kho kết quả hiện có `results.jsonl`/`results.json` cho bản ghi tương đương `attack_results`; không thêm bảng trùng lặp. Đây là test harness với mock, không phải số liệu ASR mới và không tính là PI-05/06.

## Những advisory SEC-10 còn lại

Quét mới OSV trên **94 package Python đã cài**; `npm audit` trả về 2 Moderate, 0 High/Critical. OSV là bằng chứng bổ sung, không được gọi là pip-audit. Không nâng/cài package trong đợt này theo ràng buộc không tự cài dependency của AGENTS và phạm vi người dùng; do đó các advisory dưới đây vẫn mở.

| Package hiện tại | Advisory / rủi ro | Vì sao chưa sửa / hướng xử lý sau |
|---|---|---|
| certifi 2026.7.22 | **Critical 9.1** — [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2), alias PYSEC-2026-4320. CA bundle còn root liên quan intermediate key bị lộ; có thể bị MITM khi dùng HTTPS qua kẻ tấn công trên đường truyền | Cần cập nhật bundle/package; chưa cài/nâng trong đợt này. Advisory khuyến nghị 2026.10.19 trở lên. Việc model chạy HTTP loopback không làm advisory biến mất |
| pip 26.1.2 | **Moderate 5.6** — [GHSA-qwm4-qh6w-59xr](https://github.com/advisories/GHSA-qwm4-qh6w-59xr), alias PYSEC-2026-3721. Ghi sai vị trí khi xử lý URL package từ index độc hại | Công cụ cài đặt, không phải đường xử lý giao dịch runtime. Cần pip ≥26.2.0; chưa nâng |
| postcss-selector-parser | **Moderate 5.9** — [GHSA-rj75-hqrm-r3gf](https://github.com/advisories/GHSA-rj75-hqrm-r3gf). CPU exhaustion khi parse selector | Dependency của build tool; không có chức năng nhận CSS của khách để build. Cần nâng bản sửa ≥6.1.5 trong nhánh đang dùng; chưa sửa lockfile/cài lại |
| vite 6.4.4 | **Moderate 6.9** — [GHSA-8g5g-mxqh-grgj](https://github.com/advisories/GHSA-8g5g-mxqh-grgj). Dev server có thể vượt `fs.deny` bằng query | Local demo dùng compiled assets qua FastAPI, không dùng Vite dev server. Cần nâng 6.4.5; chưa cài lại. Không đánh dấu advisory đã khắc phục |

## Quy trình, giới hạn và vận hành

- Probe đỏ thật được giữ trong `.local/security-ai-evidence`: `agent-before.log`, `agent-extra-before.log`, `AI-05-message-before.log`, `security-before.log`, `SEC-06-09-after.log` và các log E2E trước sửa. Không đưa raw log có thể chứa canary/token vào Git.
- Không thay expectation để bỏ qua lỗi. Sửa lỗi xây dựng probe gồm tên bảng `ledger_entries`/`service_notifications`, category fixture `food`, Idempotency-Key của action, parser PDF ghép các toán tử Tj. PI-02 so toàn bộ draft trước/sau thay cho tên trạng thái `DRAFT` bị đoán sai (trạng thái thực là `PENDING_OTP`); yêu cầu **không có tác dụng** được giữ và kiểm tra chặt hơn. Các lỗi fixture được phân biệt với lỗi sản phẩm.
- SEC-04 chấp nhận extra bị bỏ qua hoặc 422 đúng PDF; `status` được phép ở API admin/support/finish theo schema quyền hiện có, các extra còn lại vẫn bị chặn. Không đổi ma trận SEC-01.
- E2E mới vượt hạn mức IP do các test trước dùng chung server. Helper chỉ xóa quota `request:/api/auth/%` trên DB đã xác minh nằm trong `.local/e2e`; không nới rate limit ứng dụng. Đã bỏ đường dẫn Python chỉ hỗ trợ Windows trong helper. Lượt thực tế chạy trên Windows, chưa chạy CI Ubuntu.
- Migration 9 thêm `agent_runs.termination_reason`; chỉ chạy trên DB test. **Không restart hoặc migrate DB demo**. Bản demo đang chạy vẫn schema 8/code backend cũ. Bản dựng frontend trong `frontend/dist` được build lại bởi E2E.
- Không thực hiện API ghi hay reconcile vào DB demo. Backup/đối chiếu chỉ đọc. DB demo đang có thay đổi phiên/chat trong lúc làm việc, nên không tuyên bố toàn bộ file bất biến; đối chiếu các bảng tài chính với backup không phát hiện thay đổi. Không rollback hoạt động đang có.
- Đây là self-review, chưa có reviewer độc lập. Kiểm thử mock xác minh ranh giới và dữ liệu trên wire, không suy ra chất lượng model thật hay khả năng nhận diện mọi PII tự do không có nhãn.
- Framework `aef check .` báo thiếu `engineering.json`; không auto-initialize. Các lệnh pytest/component/E2E/reconcile thực tế được chạy trực tiếp.

Chưa làm theo phạm vi chốt: M6 gồm TRF-11, NTF-03, NF-06, SAV-01, PFM-01, QR-01, SUP-01, SUP-02, ACC-04, AUTH-23, AUTH-24. Tiếp tục hoãn NF-08, AI-14, PI-05, PI-06. Không chạy lại thí nghiệm model thật.

Rollback nếu cần: review diff so với commit Bước 0 rồi áp dụng patch ngược có chọn lọc; không dùng reset/restore toàn workspace vì có thể xóa thay đổi của người dùng. Migration 9 chỉ thêm cột nullable nên backend cũ không cần xóa cột để đọc DB test. Không khôi phục đè DB demo đang hoạt động.

Các lượt trung gian có lỗi fixture hoặc còn lỗi sản phẩm được giữ riêng trong `.local`; bảng kết quả cuối dùng lượt `final2-pytest.log` và `final-components.log`/`final-e2e.log`. Không đổi test SEC-10 thành skip/xfail, nên pytest và gate CI phụ thuộc pytest hiện vẫn đỏ đúng tình trạng dependency.
