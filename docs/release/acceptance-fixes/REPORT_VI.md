# Sửa lỗi nghiệm thu — 01/11/2026

Đã sửa và kiểm thử lại **10 ca trong phạm vi yêu cầu**, đồng thời áp dụng 4 quyết định đặc tả đã chốt. Đây là kết quả của đợt sửa lỗi sau audit, không phải tuyên bố mọi tiêu chí trong kế hoạch 121 ca đã hoàn tất.

Kết quả cuối: **271 pytest pass; 17 nhóm component test pass; 15 Playwright E2E pass; build TypeScript/Vite pass; reconcile balanced=true**, không có mismatch/journal không cân bằng. Chạy lại pytest với stdlib trace cũng pass, financial executed-line coverage **93,58%** trên 5 module cấu hình (không phải branch coverage hoặc coverage toàn app). Log và lệnh đầy đủ nằm trong thư mục này. Không cài dependency, không commit/push, không chạy lại ma trận nghiên cứu.

| Mã ca | Trước | Sau | Test/file | Lệnh đã chạy |
|---|---|---|---|---|
| TRF-14 | 40 lần tạo draft đều trả 201 | Pass: quota SQLite chung 30/user và 60/IP trong 300 giây; tính cả tra cứu lỗi; dùng chung cho draft, lookup, lưu danh bạ và draft qua agent | `backend/tests/test_TRF_14.py` (4 test); `recipient_security.py` | T1; G1; F |
| SEC-01 | Operations đọc danh sách ticket; operations/auditor đọc research | Pass: research chỉ admin khi bật sandbox; operations bị chặn ticket list; kiểm kê toàn bộ route và kiểm tra mọi cặp role bị cấm | `backend/tests/test_SEC_01.py` (18 test), `backend/tests/route_matrix.json` | T2; G2; F |
| BEN-01 | PATCH 405; tìm kiếm trả cả danh sách | Pass: sửa nickname, tìm theo nickname/tên/số tài khoản; giữ owner isolation, không đổi tài khoản nhận qua PATCH | `backend/tests/test_BEN_01.py`; `frontend/tests/e2e/acceptance-fixes.spec.ts` | T3; U3; G3; F |
| ADM-02 | Audit chỉ có trạng thái mới | Pass: actor/resource/time cùng before/after cho account, customer status/KYC và setting | `backend/tests/test_ADM_02.py` (3 test); `routes_admin.py` | T3; G3; F |
| PFM-02 | Chỉ có cảnh báo sau khi mở Insights | Pass: tạo cảnh báo trong transaction ghi sổ; chuyển nội bộ, thanh toán bill, mua thẻ tín dụng, settlement thành công; không trùng cảnh báo | `backend/tests/test_PFM_02.py` (4 test); `posting.py`, `products.py`, `settlement.py` | T3; G3; F |
| STM-01 | CSV/PDF thiếu tổng kỳ | Pass: số dư đầu/cuối, tổng credit/debit từng tài khoản từ ledger, gồm phí; PDF đã render và kiểm tra bố cục | `backend/tests/test_STM_01.py` (2 test); `insights.py` | T3; G3; F |
| DSH-01 | Reload mất lựa chọn; chỉ hiện số dư account đầu | Pass: lưu ẩn/hiện theo user; cộng tất cả payment accounts | E2E `DSH-01` trong `acceptance-fixes.spec.ts`; `Home.tsx` | G2 (đỏ); G3; F |
| AI-02 | Tool không có filter ngày/người nhận | Pass: from_date/to_date/recipient, owner-scoped, escape ký tự SQL LIKE, chặn khoảng ngày đảo ngược | `backend/tests/test_AI_02.py` (2 test); `agent_access.py`, `banking_queries.py` | T4; G4; F |
| AI-12 | Chỉ có progress; không có Stop | Pass: stream từng phần văn bản qua bộ lọc của bank; Stop hủy run, thu hồi delegation và proposal chưa duyệt; chặn tool/finish đến muộn; sửa race lịch sử đè live text | `backend/tests/test_AI_12.py` (4 test), component và E2E `AI-12`; `useBankingChat.ts`, `agent_service/main.py` | T4; C12; G4; F; L |
| AI-11 | Citation chỉ trong trace | Pass: citation nằm trong nội dung trả lời; chỉ nhận nguồn đã truy xuất và còn approved/published; mã bịa/nguồn đã thu hồi không được chấp nhận | `backend/tests/test_AI_11.py` (3 test); `agent_output.py` | T11; G4; F; L |
| AUTH-03 | Kỳ vọng cũ khác code | Pass: giữ 422 cho role/balance/balance_vnd; không tạo user | `backend/tests/test_spec_decisions.py` | F |
| ADM-03 | Probe đòi phí mới ở confirm | Pass theo quyết định: draft cũ giữ phí 0; draft mới lấy phí 1.000; hạn mức mới vẫn chặn confirm | `backend/tests/test_ADM_03.py` | G2; F |
| AI-13 | Kỳ vọng cũ bắt buộc 403 | Pass: chấp nhận 401/403; số dư, trạng thái draft và số lần thử OTP không đổi | `backend/tests/test_spec_decisions.py` | F |
| NF-07 | PDF cũ kỳ vọng phân cách khác | Pass: giữ `12,500,000 VND` | `frontend/tests/components.test.tsx` | F |

## Quyết định quyền và an toàn dữ liệu

- **Giữ support đọc alerts của chính mình.** Truy vấn lọc `owner_id` ở cả hai bảng notification. Test tạo thông báo tiền của Alice và thông báo security của support, xác nhận support không đọc hoặc đánh dấu thông báo Alice. Support không có tài khoản thanh toán; alerts của support trong luồng này không chứa dữ liệu tài chính khách.
- Operations vẫn không khóa/mở tài khoản; auditor vẫn không đọc nội dung ticket khách (404). Đây là expectation sửa theo chỉ dẫn người dùng, không phải nới quyền.
- Tất cả API research yêu cầu `role=admin` và `RESEARCH_SANDBOX_ENABLED=true`; mặc định false. Chỉ sửa cấu hình mẫu, không bật sandbox trên server demo đang chạy.
- Ma trận là danh sách route/method tường minh, gồm route ẩn và router lồng của FastAPI, các route docs và mount frontend tùy chọn. Route mới chưa khai báo sẽ làm test fail. Bộ test còn gửi request cho mọi cặp role không được phép, thay vì chỉ kiểm tra danh sách permission trong code.
- Quota recipient lấy ASGI peer, không tin `X-Forwarded-For` do client tự gửi. Bộ đếm user độc lập với IP nên đổi IP không vượt quota user; bộ đếm IP chặn xoay user. Những API chỉ đọc lại dữ liệu đã thuộc user không thực hiện tra cứu tên tài khoản mới.
- Sao kê không suy diễn số dư trước thời điểm nhập ledger. Phần đó ghi `Not recorded (pre-ledger)`; legacy history vẫn được liệt kê và ghi rõ không nằm trong ledger totals. Tổng kỳ tính cả debit đang pending và refund khi đã được ghi sổ.

## Test đỏ, expectation và sửa bộ kiểm thử

Các probe đỏ có sẵn đã được **chuyển** khỏi `docs/release/acceptance-audit/test_requirements.py` sang file backend theo mã ca. Fixture chung dùng DB pytest tạm, MFA thật và reconcile khi kết thúc. DSH-01 và phần UI AI-12 vốn nằm trong browser probe; nay có E2E/component tương ứng, còn cancellation/filter của AI-12 có test backend.

Chỉ các expectation AUTH-03, ADM-03, AI-13, NF-07 và quyền SEC-01 nêu trên đổi theo quyết định người dùng. Không đổi số tiền, trạng thái nghiệp vụ hoặc kết quả mong đợi để che lỗi.

Các sửa ở bộ kiểm thử được ghi riêng:

1. Sửa import helper theo package `tests`; lần lỗi collection không được tính là bằng chứng đỏ nghiệp vụ.
2. Test PDF dùng giải mã content stream bằng stdlib vì pypdf không có trong venv; không cài thêm. Đã kiểm tra thêm ảnh render bằng Poppler.
3. Fixture interbank dùng ngân hàng mô phỏng có thật trong catalogue (`Demo Bank A`).
4. Locator giao diện dùng tên thực `Accounts & recipients`; sau đó xác nhận test đỏ vì thiếu `Edit nickname` trên bundle cũ.
5. Các E2E bổ sung dọn **quota request đăng nhập trên DB E2E riêng** sau mỗi ca để không tiêu thụ quota của ca kế tiếp. Không thay đổi quota production; kiểm thử rate limit backend vẫn dùng bộ đếm thật, không reset giữa các request của một ca.
6. Trong identity E2E, bỏ thao tác bấm Show lần hai khi quay về Home, thay bằng kiểm tra Hide đang hiện: DSH-01 nay nhớ lựa chọn trước đó. Assertion số dư 100.000 và toàn bộ luồng recovery/revoke giữ nguyên.
7. E2E AI-12 phát hiện lịch sử trả về chậm ghi đè live text. Đã sửa code để không ghi đè trong khi request đang hoạt động; không đổi assertion live text/cancellation.

## Các lần chạy theo nhóm

| Lượt | Pytest | Component | E2E | Reconcile |
|---|---|---|---|---|
| G1 | 228 pass, 13 probe còn đỏ/khác đặc tả của các nhóm sau | 15 pass | 12 pass | Cân bằng |
| G2 | 246 pass, 6 probe nhóm sau còn đỏ | 15 pass | 11 pass, 3 fail: DSH, locator BEN, quota đăng nhập của fixture | Cân bằng |
| G3 | 257 pass, AI-02 còn đỏ | 15 pass | 13 pass, identity còn bấm Show dù DSH đã nhớ lựa chọn | Cân bằng |
| G4 | 266 pass | 17 pass | 14 pass, AI-12 lộ race history/live text | Cân bằng |
| F — sau tất cả sửa lỗi | **271 pass** | **17 pass** | **15 pass** | **Cân bằng** |

Số test tăng trong quá trình chuyển probe và bổ sung kiểm tra. Các log lịch sử giữ nguyên kết quả đỏ, không thay thế bằng log xanh.

## Lệnh đã chạy

Các lệnh dưới đây chạy từ root repo, trừ lệnh npm/Playwright chạy trong `frontend`. Python là venv có sẵn. `*-commands.json` ghi argv, cwd và exit code thực tế của từng lượt G1/G2/G3/G4/F.

```powershell
# T1: đỏ rồi xanh
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_TRF_14.py -q
# T2: đỏ rồi xanh
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_SEC_01.py -q
# T3: đỏ rồi xanh; có lượt bổ sung ADM/PFM và lượt kèm SEC
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_BEN_01.py backend/tests/test_ADM_02.py backend/tests/test_PFM_02.py backend/tests/test_STM_01.py -q
# U3: bundle trước sửa UI, xác nhận thiếu Edit nickname
npx --no-install playwright test tests/e2e/acceptance-fixes.spec.ts -g BEN-01
# T4: đỏ rồi các lượt xanh theo file
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_AI_02.py backend/tests/test_AI_12.py -q
# T11: đỏ rồi xanh cùng nhóm 4
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_AI_11.py -q
# C12: đỏ rồi xanh; cũng có trong mọi lượt kiểm tra nhóm
npm run test:components
# G1/G2/G3/G4/F: thực tế chạy riêng với g1, g2, g3, g4, final
backend/.venv/Scripts/python.exe .local/acceptance-fixes/check_group.py final
# Wrapper trên gọi: pytest -q (cwd backend), hai lệnh npm dưới và reconcile trên DB E2E mới
npm run test:components
npm run test:e2e
backend/.venv/Scripts/python.exe scripts/reconcile.py --db <DB-E2E-trong-final-commands.json>
# L: hai process HTTP thật + Qwen/Ollama, DB mới hoàn toàn
backend/.venv/Scripts/python.exe scripts/check-agent-service.py
# Coverage: chạy lại toàn bộ pytest với stdlib trace, không thêm thư viện
backend/.venv/Scripts/python.exe scripts/financial-coverage.py
```

## LLM thật, dữ liệu và triển khai

Kiểm tra Qwen2.5:7b + nomic-embed-text qua hai process HTTP riêng đã pass: balance, RAG, transfer proposal, cancellation. RAG trả ngay `[KB-savings]` trong câu trả lời; có sự kiện text trước complete. Số dư Alice vẫn 12.500.000 và proposal chuyển tiền chưa được thực hiện. Đây là smoke test chức năng, không phải chạy lại AI-14/PI-05/PI-06 hoặc đo ASR mới.

Không ghi vào DB demo: pytest dùng `tmp_path`; E2E dùng `.local/e2e/run-*`; LLM dùng `.local/full-roadmap/agent-check-*`. Hai file DB gốc khớp SHA256 baseline (`db-hashes.json`). Server local hiện có không bị restart, không thay đổi environment hay DB của server đó. **Backend đang chạy cần được khởi động lại khi người dùng muốn áp dụng code mới.**

Tự review các đường quota, owner/role, transaction notification, ledger totals, cancellation race và output filtering. Chưa có review độc lập hoặc remote CI; không tuyên bố release/merge approval. Không xóa/reset các thay đổi có sẵn của người dùng.

## Chưa làm trong đợt này

- **AI-14, PI-05, PI-06:** hoãn theo yêu cầu; không chạy lại thí nghiệm nghiên cứu, không cập nhật số liệu ASR/utility cũ.
- Không còn ca sửa lỗi nào trong 10 ca được chỉ định bị bỏ dở. Server demo chưa được restart để tuân thủ yêu cầu không ghi DB demo.

Rollback: các thay đổi đợt này không cần migration mới. Nếu cần hoàn tác, áp dụng lại snapshot/diff đã được review cho đúng các file liên quan; không reset toàn repo vì có nhiều thay đổi từ các đợt trước. Không chỉnh số dư hay xóa ledger để rollback.
