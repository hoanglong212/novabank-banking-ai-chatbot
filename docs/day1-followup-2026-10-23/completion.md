# NovaBank — sửa lỗi ngày 1 và nền tảng JWT/session

## Kết quả

- Gỡ create_support_ticket khỏi tool schema, dispatcher, policy allowlist và routing. Chat từ chối tạo ticket; UI không còn gợi ý tạo ticket. Dữ liệu ticket cũ được giữ nguyên.
- Database.connect nay commit/rollback và luôn close trong finally. Test giữ tham chiếu connection sau cả thành công và exception đều xác nhận connection đã đóng.
- Benchmark chạy lại đủ 20 native + 20 guarded, exit 0, dọn database tạm thành công; evidence cũ được giữ nguyên.
- Ollama request gửi keep_alive=60m, có thể override OLLAMA_KEEP_ALIVE; /api/ps được lưu trong evidence.
- Backend JWT/session, CSRF, Origin, rate limit; frontend login/logout/restore session đã triển khai. Tài khoản seed bằng cấu hình cục bộ; không còn API phát demo token hay bearer fallback.
- Presidio chưa tích hợp production; không chỉnh recognizer trên tập evaluation cũ.

## Ollama sau sửa

| Chỉ số | Kết quả |
|---|---:|
| Native đúng tool | 16/20 |
| Native đúng tool + arguments | 15/20 |
| Guarded qua business checks | 20/20 |
| Guarded median / p90 / p95 / max | 0.728 / 0.834 / 0.958 / 1.682 giây |
| Native median / p90 / p95 / max | 0.324 / 0.352 / 0.359 / 0.523 giây |

Guarded gồm proposal của model, binding, policy, tool, audit SQLite và render câu trả lời bằng code ứng dụng; không có lượt LLM thứ hai để viết câu trả lời. Không bao gồm HTTP frontend, truyền mạng tới browser hoặc render UI. Một lần mỗi ca, máy đã được warm; không suy rộng thành SLA. FAQ mới kiểm tra schema và có thực thi/trả lời, chưa chấm semantic correctness.

Bổ sung cho lần đo ban đầu (không chạy lại): guarded median 0.695, p90 1.044, max 1.512 giây; native p90 0.475, max 4.704 giây. Các số mới ở bảng trên thuộc lần đo sau sửa, không trộn hai lượt.

Nguồn guarded: 13 ollama_tool, 2 ollama_tool_bound, 4 application_template, 1 application_fallback. Các nhãn này không đồng nghĩa model tự lập luận đúng.

### Phân loại 5 ca native sai ở lần đo ban đầu

| Ca | Đề xuất sai | Phân loại / ứng phó |
|---|---|---|
| balance-vi | Tự sinh account_id Demo123 | Intent cốt lõi: giữ binding từ yêu cầu/session, không tin ID model |
| ambiguous-tx | Gọi cả TX-1001 và TX-1002 | Mơ hồ/nhiều tài nguyên: ứng dụng yêu cầu chọn một |
| greeting | Gọi FAQ cho Hello | Routing không cần thiết; dùng template |
| transfer-refusal | Dùng get_account_balance với ID Bob | Yêu cầu ghi ngoài phạm vi; ứng dụng từ chối |
| ticket-readonly-gap | Đề xuất tạo ticket | Trước sửa prompt còn cho phép; nay gỡ tool ghi ở mọi lớp |

Không có bằng chứng cần thay model ngay. Sau sửa native vẫn 15/20 nhưng guarded đã chặn ca ticket; raw proposals mới ở ollama.json.

## PII: đo kết quả thay vì chỉ arguments

Giữ nguyên 48 câu evaluation và masked text cũ. Với 18 ca đủ điều kiện, thực thi cả yêu cầu gốc và đã che qua binder + gateway + dispatcher thật trong database tạm, danh tính Alice. So sánh result và câu trả lời được render:

- 12 ca đổi binding; **11 ca sai kết quả nghiệp vụ**.
- pii-036 (ACC-ALICE-001): bỏ account_id explicit nhưng mặc định vẫn là tài khoản Alice, kết quả không hỏng.
- pii-031/032/033: ID số không được phép bị mất, yêu cầu chuyển thành trả số dư Alice thay vì từ chối — 3 ca hỏng.
- pii-037 (ACC-BOB-001), pii-038 (ACC-NOBODY-001): mất ID đích, trả số dư Alice thay vì từ chối — 2 ca hỏng.
- pii-039 đến pii-044: cùng yêu cầu tài khoản Bob kèm email/điện thoại; mất ID đích — 6 ca hỏng.
- 7/18 ca còn lại giữ kết quả: ba câu hỏi self-balance không có ID đích, ba câu có mã TX và một câu explicit Alice. Không che được PII không có nghĩa là bảo vệ thành công dù nghiệp vụ vẫn đúng.

Đây là đo cách tích hợp ngây thơ “che trước binder”, chưa phải pipeline mapping được chốt, chưa gọi model trong phép so sánh này. 30 ca khác chưa được chấm kết quả nghiệp vụ. Không có truy cập được tài khoản Bob: lỗi là đổi nghĩa sang tài khoản Alice.

**Chuỗi phi PII bị che:** pii-051, `Số tiền 0912345678 VND` bị che thành `Số tiền <VN_PHONE> VND`. Các mã TX trong corpus không bị che. Hai ca bỏ sót tài khoản có nhãn `STK:` và `Tài khoản của tôi là`; ba ca CCCD bỏ sót dùng nhãn diễn đạt khác CCCD sát số. Chưa sửa regex và chưa báo số đo cải thiện.

Không áp dụng ngay kiểm tra mã tỉnh/giới tính như một bộ lọc bắt buộc: cần đặc tả đáng tin và tập mới trước; quy tắc quá chặt có thể bỏ sót dữ liệu nhạy cảm gõ sai. Nhận diện PII và xác minh giấy tờ là hai bài toán khác nhau.

## Bằng chứng và tiêu chí

| Tiêu chí | Bằng chứng |
|---|---|
| Chặn tool ghi ngay cả model cố gọi | test_day1_fixes.py + cập nhật test_chat/test_reliability |
| Connection đóng sau commit/rollback | test_connection_closed_after_commit_and_rollback; benchmark exit 0 |
| JWT/cookie/CSRF/logout/reload | test_sessions.py |
| Chặn truy cập chéo, legacy token | test_chat.py + test_sessions.py |
| Rate limit đăng nhập | test_login_rate_limit_and_origin |
| Kết quả PII thực thi thật | pii-business.json, không tuning |
| Latency và raw proposals | ollama.json |

Lệnh đã chạy:

```powershell
# backend/
rtk proxy .\.venv\Scripts\python.exe -m pytest -q
# frontend/
rtk proxy npm run build
rtk proxy npm run test:components
# repository root
rtk proxy .\backend\.venv\Scripts\python.exe scripts/benchmark_day1.py --output docs/day1-followup-2026-10-23
rtk proxy .\backend\.venv\Scripts\python.exe scripts/evaluate_pii_business.py
rtk proxy .\backend\.venv\Scripts\python.exe scripts/verify-auth-live.py
```

Backend full suite xác nhận cuối: 64 passed, 1 warning trong 34.66 giây. Build và sáu nhóm component checks passed. Live isolated server check passed, gồm login, assets, balance, denial, ownership, dry-run, logout và cleanup. Build cảnh báo không có Tailwind utility; pytest có Starlette/httpx deprecation warning, không làm fail. `git diff --check` và Node syntax check của browser test đều passed.

Browser CDP identity check đã cập nhật và chạy bằng `npm run test:identity`, nhưng FAILED: timeout chờ login/profile. Kiểm tra read-only sau lỗi cho thấy trang `chrome-error://chromewebdata/`, `127.0.0.1 refused to connect`, `ERR_CONNECTION_REFUSED`: frontend :5173 chưa phục vụ. Chưa chạy được các assertion login/reload trong browser. Dừng theo yêu cầu người dùng khi gặp lỗi; không coi lỗi môi trường này là bằng chứng code login hỏng. Chưa kiểm tra HTTPS thiết bị thật. Independent review: pending. Chưa coi toàn bộ milestone hoặc MVP hoàn tất.

## Phạm vi thay đổi và phần còn lại

Backend: database.py, auth.py, sessions.py, main.py, agent.py, banking_workflow.py, tools.py, gateway.py, dependency/config và tests. Frontend: App, api/types, hook phiên, Topbar, login CSS, suggestions và component/browser tests. Scripts: benchmark, PII business evaluation, auth initializer và acceptance check. Hướng dẫn: README, AUTH_SETUP, plan ledger và báo cáo này.

Đã thêm thông tin đăng nhập ngẫu nhiên vào backend/.env (ignored), không in bí mật ra log. Database demo hiện có không bị dùng trong acceptance test; auth tables/user seed được tạo khi backend thực tế khởi động lại. Không commit/push.

Phần tiếp theo: tích hợp PII bằng mapping đúng, LangGraph, chuyển tiền nguyên tử và QR; kiểm tra mốc ngày 3 vẫn chưa được thực hiện. Rollback theo AUTH_SETUP.md, không xóa dữ liệu/evidence cũ.
