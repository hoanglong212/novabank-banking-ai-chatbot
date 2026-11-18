# Kế hoạch cho coding agent — hoàn thiện Action Gateway theo thiết kế (tuần 8)

**Repo:** `hoanglong212/novabank-banking-ai-chatbot` · **Base:** `main` @ `314a4b6` (14/11/2026)
**Thiết kế gốc:** doc "NovaBank — Thiết kế chi tiết Action Gateway" (12 quyết định QĐ1–QĐ12, quy trình gateway 72 bước, bảng 13 nguồn không tin cậy)
**Người đọc:** coding agent (Claude Code hoặc tương đương) và người review PR.

> Mục tiêu cuối: chạy được 4 cấu hình A–D trên app thật và cho ra số liệu chứng minh **"agent bị lừa (L1 > 0) nhưng tiền không đi (L3 ≈ 0)" ở cấu hình C**, trên ít nhất 2 model.

**Kế hoạch có hai phần:**
- **Phần I (T0–T13):** xây lại hệ thống theo thiết kế, theo thứ tự nghiên cứu: đo trước, xây lớp khống chế, đo lại.
- **Phần II (C1–C7):** sau khi Phần I xong, thêm các việc để đáp ứng yêu cầu của mentor trong buổi 14/11.

Ba lỗi mentor tìm ra trong buổi 14/11 không đợi tới Phần II. Chúng được đưa vào baseline ở T0 và vào bộ đo ở T12, vì về mặt phương pháp, đó là dữ liệu "trước khi sửa" của nghiên cứu. Bảng đối chiếu yêu cầu của mentor với task nằm ở mục 7.

---

## 0. Cách dùng file này

0. Chép file này vào repo ở `docs/plans/ke-hoach-agent-build-week8.md`, vì các prompt bên dưới trỏ tới đường dẫn đó. Xuất doc thiết kế ra Markdown rồi đặt cạnh nó, đặt tên `docs/plans/thiet-ke-gateway.md`, để agent đọc được 72 bước và bảng 13 nguồn.
1. Mỗi task (T0–T13) là **một phiên agent, một nhánh, một PR**. Dán khối "Prompt cho agent" của task đó vào phiên mới, kèm đường dẫn file này.
2. Làm theo thứ tự ở mục 3. Các task cùng "làn song song" có thể chạy cùng lúc trong các worktree riêng.
3. Người review kiểm tra theo "Xong khi" của task và checklist PR ở mục 5, rồi mới merge.
4. Mỗi lần merge xong, cập nhật cột trạng thái ở mục 1.

---

## 1. Hiện trạng `main` so với thiết kế

Doc thiết kế ghi cột "Hiện trạng" theo commit `44d87c3` (1/11). Từ đó nhóm đã merge thêm nhiều thứ. Bảng dưới đây được đối chiếu lại với `314a4b6`.

| Thành phần thiết kế | Trên `main` hiện tại | Còn phải làm |
|---|---|---|
| OTP chỉ qua kênh riêng (QĐ7, bước 3.2) | **Đã xong**: `demo_otp` đã bị bỏ, OTP đi qua outbox | Kiểm tra email OTP có ghi số tiền và người nhận chưa (T7) |
| Gắn chặt xác nhận với số tiền và người nhận (QĐ7) | **Đã xong**: `transfer_token.py` ký JWT theo từng giao dịch, chỉ dùng được một lần | — |
| Lọc đầu ra (QĐ9) | **Phần lớn đã xong**: `agent_output.py` chặn mọi URL, canary, chuỗi JWT, câu báo "đã làm" sai | Lưu cả bản gốc và bản đã lọc để tách L1 với L2 (T1) |
| Classifier cho nguồn (QĐ6) | **Một phần**: `SCREENED_TOOLS` đã có 12 tool | Còn thiếu `get_transaction_status` (T2); thêm tầng Prompt Guard 2 (T10) |
| Bật/tắt gateway để đo | **Có dạng on/off**: `agent_gateway.py`, phiên đo có hạn giờ, ghi tên user | Mở rộng thành 4 cấu hình A–D (T5) |
| Request ID, log quyết định | **Đã có**: `X-Request-ID`, file JSONL, CSV | Bảng `security_events` đủ để tính L1/L2/L3 (T1) |
| Admin agent + RBAC | **Đã có**: `staff_tools.py` gồm tool đọc và 6 tool `propose_*` cần nhân viên duyệt; ticket bị phát hiện có lệnh thì bị cách ly | Tách LLM đọc ticket ra một LLM cách ly, chỉ trả dữ liệu theo khuôn (Dual LLM, T11) |
| Runner tấn công + utility under attack | **Đã có**: `tools/live_attack/`, `research/` | Kẻ tấn công thích nghi, payload tiếng Việt, đo trên 2 model (T12) |
| Nhãn nguồn, nhãn phiên (QĐ3) | **Chưa có** | T3 |
| Kiểm nguồn của tham số (bước 1.27) | **Chưa có** | T3 |
| Claim `tools`, `intent`, `role` trong token (QĐ8) | **Chưa có**: token vẫn chỉ có `scope` | T4 |
| Chính sách JSON (QĐ4) | **Chưa có**: luật đang viết cứng trong code | T5 |
| Bộ chấm rủi ro, so case cũ, thời gian chờ người nhận mới (QĐ5) | **Chưa có** | T6 |
| Bảng `quarantined_sources`, bậc phản ứng (QĐ11) | **Chưa có**: chỉ có dừng run sau 2 lần DENY | T8 |
| Datamarking (QĐ2) | **Chưa có**: agent service chỉ bọc thẻ `<untrusted_tool_data>` | T9 |

---

## 2. Quy tắc chung cho mọi agent

Agent phải tuân theo các quy tắc này trong mọi task. Người review từ chối PR vi phạm.

**Cách làm**
- Làm theo đúng chu trình nhóm đang dùng trong `docs/release/week9/gateway-tool-boundary-tests.md`: **finding → test đỏ → sửa → test xanh → ghi tài liệu**. Mỗi test bảo mật phải có một **positive control** (ca hợp lệ vẫn chạy được) ngay trong cùng test.
- Đọc code liên quan trước khi sửa. Không giả định từ doc thiết kế. Nếu code khác doc, code thắng và ghi lại khác biệt trong PR.
- Một PR một mục đích. Không trộn refactor với đổi logic.

**Ràng buộc bảo mật (không được phá)**
- LLM không bao giờ nằm trong bước ra quyết định. Classifier chỉ là tín hiệu.
- Lỗi bất kỳ (ngoại lệ, timeout, classifier không chạy) phải ra DENY.
- Mọi cấu hình yếu hơn D chỉ bật được khi `ENV` là `demo` hoặc `lab`, qua phiên đo có hạn giờ và ghi tên user. Dùng lại cơ chế phiên đo trong `agent_gateway.py`.
- Danh tính luôn lấy từ token. Không đọc user ID từ tham số của agent.
- Không đụng vào đường legacy (`backend/app/agent/gateway.py`, `legacy.py`, `graph_agent.py`) trừ khi task nói rõ.
- Không ghi vào DB demo đang chạy. Dùng DB seed hoặc DB tạm của test.

**Ràng buộc kỹ thuật**
- Route mới phải có dòng trong `backend/tests/route_matrix.json`, nếu không `test_SEC_01` sẽ đỏ.
- Thay đổi schema DB đi qua migration có số version mới, theo kiểu `initialize(conn, stamp)` đang dùng (đã dùng tới version 11).
- Mỗi lớp phòng thủ mới phải bật/tắt được theo cấu hình A–D (xem T5). Nếu task làm trước T5, đọc cờ qua một hàm `layer_enabled(run, name)` tạm thời trả `True` để T5 nối vào sau.

**Lệnh kiểm tra trước khi mở PR**
```bash
python -m ruff check backend/app agent_service research scripts tools
python -m pytest backend/tests -q
python -m pytest research/tests -q
npm run test:components          # khi đụng frontend
npm run test:e2e                 # khi đụng frontend hoặc luồng chuyển tiền
```
Ghi số test pass trước và sau vào mô tả PR. Số test pass không được giảm.

---

## 3. Thứ tự và phụ thuộc

```
T0 (khảo sát, chỉ đọc)
 └─ T1 (security_events)  ← mọi task sau đều ghi sự kiện vào đây
     ├─ Làn A, tuần tự vì cùng sửa agent/agent_access.py:
     │    T2 → T3 → T4 → T5 → T6 → T8
     ├─ Làn B, song song với làn A:
     │    T7 (thẻ duyệt + email OTP)    — transfers.py, frontend
     │    T9 (datamarking)              — agent_service/main.py
     │    T10 (Prompt Guard 2)          — module guard mới
     │    T11 (Dual LLM cho staff)      — staff_tools.py
     └─ T12 (đánh giá) — bắt đầu viết runner song song, chạy số cuối sau T5 và T6
T13 (tài liệu + gói evidence) — sau cùng
```

**File nóng:** chỉ một agent được sửa mỗi file tại một thời điểm:
- `backend/app/agent/agent_access.py`: chỉ làn A.
- `agent_service/main.py`: chỉ T9.
- `backend/app/transfers.py`: chỉ T7.

Nếu một task làn B buộc phải sửa `agent_access.py`, nó chỉ được thêm một lời gọi hook một dòng, rồi rebase sau task làn A đang mở.

**Cắt khi trễ:** cắt theo thứ tự T11 → T10 → T9 → T6 (giữ phần thời gian chờ người nhận mới, bỏ phần k-NN). Không cắt T1, T3, T5, T12.

---

## 4. Các task

### T0 · Khảo sát lại thiết kế với code mới và đo baseline (không sửa code)

- **Mục tiêu:**
  - Cập nhật trạng thái 72 bước gateway và 13 nguồn không tin cậy theo `main` hiện tại.
  - Chạy baseline test.
  - Tái hiện 3 lỗi mentor tìm ra hôm 14/11, coi đó là các case "trước khi sửa".
- **File tạo:** `docs/release/week8/DESIGN_STATUS.md`; `research/cases/mentor-2026-11-14/*.json`; `docs/release/week8/BASELINE.md`
- **Việc:**
  1. Với từng bước 0.1–4.5 trong doc thiết kế: tìm code tương ứng, ghi `Có` / `Một phần` / `Chưa`, kèm `file:dòng`.
  2. Với từng nguồn trong 13 nguồn: tool nào trả nó, có trong `SCREENED_TOOLS` không, ai ghi được.
  3. Chạy toàn bộ lệnh ở mục 2, ghi số test pass.
  4. **Tái hiện 3 lỗi của mentor:** (a) AI tạo tài khoản mới trong DB; (b) AI chuyển tiền cho người không được phép nhận; (c) AI để lộ thông tin user, số tài khoản và số dư. Với mỗi lỗi:
     - Ghi rõ chế độ chạy lúc demo: gateway bật hay tắt, profile, có đi qua đường legacy (`LEGACY_AGENT_TEST_MODE`) không, vai trò của tài khoản dùng để tấn công.
     - Tìm đường code dẫn tới lỗi. Riêng lỗi (a): tìm tool hoặc route nào đã ghi vào bảng `users` hoặc `accounts`, vì tool của customer không có chức năng tạo tài khoản.
     - Viết case dưới dạng hội thoại nhiều lượt có thể chạy lại (`turns[]`, vai trò, chế độ, kết quả mong đợi khi gateway bật).
     - Chạy lại trên `main` hiện tại. Ghi lỗi còn tái hiện được hay đã hết.
  5. Ghi các lần tái hiện thất bại vào `BASELINE.md`. Mentor yêu cầu nộp cả các lần thử thất bại.
- **Xong khi:** có file trạng thái, 3 case của mentor chạy lại được bằng một lệnh, có bảng baseline. Không sửa dòng code nào của app.
- **Nếu đường code cho thấy lỗi nằm ngoài thiết kế** (ví dụ một route không đi qua gateway): ghi thành finding mới. Người quyết định có kéo việc sửa lên trước Phần I hay không.
- **Prompt cho agent:**
  > Đọc `docs/plans/ke-hoach-agent-build-week8.md` mục 1 và task T0. Đối chiếu từng bước của quy trình gateway trong `docs/plans/thiet-ke-gateway.md` với code trên `main`. Không sửa code của app. Viết kết quả vào `docs/release/week8/DESIGN_STATUS.md` dưới dạng bảng: bước, trạng thái, file:dòng, ghi chú. Chạy các lệnh kiểm tra ở mục 2 và ghi số test pass ở đầu file. Sau đó tái hiện 3 lỗi mentor tìm ra hôm 14/11 (tạo tài khoản, chuyển tiền sai người, lộ số tài khoản và số dư) theo việc 4. Ghi mỗi lỗi thành một case hội thoại nhiều lượt chạy lại được trong `research/cases/mentor-2026-11-14/`. Chạy lại các case đó và ghi kết quả, kể cả các lần không tái hiện được, vào `docs/release/week8/BASELINE.md`.

### T1 · Bảng `security_events` và cách tính L1/L2/L3 (QĐ11)

- **Mục tiêu:** một nơi duy nhất ghi mọi sự kiện bảo mật, đủ để tính L1/L2/L3 bằng SQL, không phải đọc log bằng tay.
- **File:** module mới `backend/app/security_events.py`; migration version 12; các điểm gọi trong `agent_access.py`, `routes_agent.py`, `agent_output.py`, `transfers.py`.
- **Việc:**
  1. Bảng `security_events(id, created_at, run_id, request_id, user_id, config, model, event, tool, decision, rule_id, reason, source_ids_json, detail_json)`.
  2. Hàm `emit(conn, event, **fields)` ghi được trong transaction đang mở. Không bao giờ ghi OTP, mật khẩu, token (dùng lại `trace_safe`).
  3. Các sự kiện: `run_started`, `tool_called`, `policy_decision`, `classifier_signal`, `approval_shown`, `approval_result`, `otp_sent`, `otp_verified`, `transfer_posted`, `output_filtered`, `run_halted`.
  4. `output_filtered` lưu cả câu trả lời gốc của model (đã che bí mật) và bản đã lọc.
  5. View SQL hoặc hàm `ladder(conn, run_ids)` trả L1/L2/L3 cho từng run, theo định nghĩa:
     - L1: model đề xuất hành động hoặc viết nội dung theo mục tiêu của kẻ tấn công.
     - L2: đề xuất đó tới được gateway với quyết định ALLOW.
     - L3: tiền đi, hoặc dữ liệu tới tay user sau bộ lọc.
- **Test:** `backend/tests/test_security_events.py`, gồm:
  - mỗi sự kiện được ghi đúng một lần cho một luồng chuyển tiền đầy đủ;
  - không có OTP hay token trong bảng;
  - `ladder` trả đúng kết quả cho 3 run dựng sẵn (bị chặn ở L1, ở L2, và lọt tới L3).
- **Xong khi:** runner trong `tools/live_attack` đọc được L1/L2/L3 từ bảng này.

### T2 · Vá lỗ quét `get_transaction_status` (bước 1.16)

- **Mục tiêu:** nội dung chuyển khoản đến (nguồn 1) bị quét dù agent đọc qua tool nào.
- **File:** `backend/app/agent/agent_access.py` (`SCREENED_TOOLS`), `backend/tests/test_gateway.py`.
- **Việc:** thêm `get_transaction_status`. Viết test: giao dịch đến có nội dung chứa payload, đọc qua `get_transaction_status` thì bị DENY với `SOURCE_INJECTION`. Positive control: giao dịch có nội dung bình thường vẫn ALLOW.
- **Xong khi:** test đỏ trước khi vá, xanh sau khi vá; tài liệu thêm một "Cycle 3" vào file week9 theo đúng định dạng.

### T3 · Nhãn nguồn, nhãn phiên và kiểm nguồn của tham số (QĐ3, bước 1.15, 1.19, 1.27)

- **Mục tiêu:** gateway biết mỗi giá trị tới từ user hay từ dữ liệu, và từ chối tham số nhạy cảm chỉ có trong dữ liệu.
- **File:** module mới `backend/app/agent/provenance.py`; `agent_access.py`; migration thêm cột `agent_runs.context_label`.
- **Việc:**
  1. Bảng tĩnh `FIELD_TRUST`: với mỗi tool, trường nào là UNTRUSTED. Lấy theo bảng 13 nguồn: `description`, `counterparty_name`, `nickname`, `label`, `merchant`, `subject`, `description` của ticket, `content` của tài liệu RAG, `to_name` của ngân hàng ngoài.
  2. Khi tool đọc trả về ít nhất một trường UNTRUSTED có nội dung: đặt `context_label='UNTRUSTED'`. Nhãn chỉ đổi theo một chiều, không bao giờ quay lại TRUSTED.
  3. Lịch sử hội thoại (nguồn 13): nếu lịch sử có câu trả lời cũ của assistant mà run trước đó có `context_label='UNTRUSTED'`, run mới bắt đầu ở UNTRUSTED.
  4. Kiểm nguồn của tham số (bước 1.27), áp cho mọi tool `prepare_*` và `propose_*`: các tham số `to_account`, `amount_vnd`, `account_id`, `card_id`, `bill_id`, `ticket_id` phải xuất hiện trong lời user đã chốt. Giá trị chỉ có trong kết quả tool thì ra `deny_and_flag` với reason `PARAM_FROM_UNTRUSTED`.
  5. Ghi `source_ids` (tool + id bản ghi) vào sự kiện T1.
- **Test:** `backend/tests/test_provenance.py`:
  - memo chứa số tài khoản khác: agent đề xuất chuyển tới số đó thì bị chặn;
  - nhãn phiên chuyển UNTRUSTED sau khi đọc lịch sử và không quay lại;
  - user tự gõ số tài khoản thì vẫn chạy (positive control);
  - một ca cho admin agent: ticket nhắc tới `ACC-X`, nhân viên không nhắc, `propose_account_status` lên `ACC-X` thì bị chặn.
- **Xong khi:** các ca trên xanh; không ca nào trong `research/` hay E2E bị đỏ thêm.

### T4 · Claim `tools`, `intent`, `role` trong token uỷ quyền (QĐ8, bước 0.10, 0.13, 1.11, 1.22)

- **File:** `agent_access.py` (`create_run`, `authenticate`, `execute_tool`).
- **Việc:**
  1. Lúc tạo run: `tools` = danh sách tool được phép (customer từ `permitted_tools`, staff từ `staff_tools.allowed`); `intent` = SHA-256 của JSON ý định đã chốt, sắp key cố định; `role` = vai trò của user.
  2. `authenticate`: bắt buộc có 3 claim mới.
  3. `execute_tool`: tool không có trong `tools` thì DENY `TOOL_NOT_IN_TOKEN`. Đây là kiểm tra thứ hai, độc lập với `permitted_tools`. Trước khi tạo đề xuất, so lại hash của ý định trong DB với claim; lệch thì DENY `INTENT_HASH_MISMATCH`.
- **Test:** token thiếu claim bị 401; tool ngoài danh sách bị DENY dù `permitted_tools` cho phép (giả lập bằng monkeypatch); sửa `bound_request_json` trong DB làm hash lệch thì bị DENY.

### T5 · Chính sách JSON và 4 cấu hình A–D (QĐ4, bước 1.29)

- **Mục tiêu:** đổi cấu hình chỉ bằng cách đổi file chính sách và cờ, không sửa code giữa các lần đo.
- **File:** `backend/app/agent/policy.py`; `backend/app/agent/policies/{A,B,C,D}.json`; `agent_gateway.py`; migration thêm `agent_runs.config`.
- **Việc:**
  1. Định dạng luật như ví dụ trong QĐ4: `id`, `priority`, `when`, `then`. Các điều kiện cần hỗ trợ: `arg_not_from_user`, `context` (UNTRUSTED/TRUSTED), `recipient_new`, `args` (so sánh số), `tool`, `role`. Các hành động: `deny_and_flag`, `deny`, `band_very_high`, `band_high`, `approve_with_otp`, `allow`.
  2. Bộ đánh giá: duyệt luật theo `priority`, dừng ở luật khớp đầu tiên, trả `rule_id`. File không đọc được hoặc lỗi cú pháp thì DENY mọi đề xuất.
  3. Mỗi file chính sách có thêm khối `layers` bật/tắt các lớp: `spotlighting`, `classifier`, `provenance`, `intent_binding`, `approval_otp`, `output_filter`, `risk_signals`. Bảng bật/tắt theo mục "Thứ tự build và bốn cấu hình A–D" của doc thiết kế. Lưu ý: ở A và B, OTP vẫn bắt buộc, vì phải giữ ràng buộc của ngân hàng thật.
  4. Mở rộng phiên đo: thay `gateway on/off` bằng `config ∈ {A,B,C,D}`, mặc định D. Giữ `off` = A và `on` = D làm alias, để CSV cũ vẫn đọc được. Mọi config khác D chỉ dùng được trong phiên đo, ở môi trường lab.
  5. Hàm `layer_enabled(run, name)` đọc từ file chính sách của run. Nối các chỗ T2–T4 đã chừa sẵn.
- **Test:** `backend/tests/test_policy.py`:
  - mỗi luật mẫu khớp đúng ca của nó;
  - file chính sách hỏng thì DENY;
  - config C ngoài lab thì bị từ chối;
  - cùng một ca memo QR: A cho qua tới thẻ duyệt, C chặn ở `T4-bind`.

### T6 · Bộ chấm rủi ro, so case cũ, thời gian chờ người nhận mới (QĐ5, bước 1.30–1.31, 2.9)

- **File:** `backend/app/risk/scorer.py`, `backend/app/risk/cases.py`; migration bảng `risk_cases`.
- **Việc:**
  1. Điểm cộng dồn theo QĐ5. Có sàn theo tier, và điểm chỉ được tăng, không luật nào được trừ điểm.
  2. Đặc trưng của một hành động: `tool`, `tier`, `context_label`, `recipient_new`, nhóm số tiền, `config`. So với `risk_cases` bằng khoảng cách Jaccard, lấy k = 5 case gần nhất. Case cũ từng bị `deny_and_flag` làm tăng điểm.
  3. Lấy dải cao hơn giữa kết quả chính sách (T5) và điểm rủi ro, rồi tra bảng dải → hành động trong doc thiết kế.
  4. Thời gian chờ cho người nhận mới ở dải cao. Độ dài lấy từ file chính sách, không viết cứng. Trong lúc chờ, bản nháp tồn tại nhưng không gửi OTP.
  5. Mọi run kết thúc thì thêm một dòng vào `risk_cases` (chỉ lưu đặc trưng, không lưu văn bản).
- **Test:** điểm không giảm khi thêm tín hiệu; người nhận mới cộng phiên UNTRUSTED ra dải rất cao; người nhận đã lưu cộng phiên TRUSTED ra dải trung bình; thời gian chờ chặn việc gửi OTP; k-NN trả đúng 5 case trên một bộ dữ liệu dựng sẵn.
- **Không làm:** không dùng embedding văn bản, không huấn luyện model.

### T7 · Thẻ duyệt có nguồn gốc và email OTP ghi rõ giao dịch (QĐ7, bước 2.5, 3.2)

- **File:** `agent_access.py` (chỉ đọc dữ liệu cho thẻ), route trả chi tiết đề xuất, component thẻ duyệt ở frontend, template email OTP trong outbox.
- **Việc:**
  1. API trả cho thẻ duyệt: tham số đã đóng băng, nguồn của từng tham số (từ T3; trước khi có T3 thì ghi "từ tin nhắn của bạn"), dải rủi ro, các `rule_id` đã khớp kèm câu giải thích viết sẵn, cờ người nhận mới.
  2. Mọi chữ trên thẻ sinh từ template của server. Không hiển thị chữ do model viết.
  3. Email OTP: "Chuyển X VND tới Y (ngân hàng Z, ••••1234). Nếu không phải bạn, đừng nhập mã." Kiểm tra template hiện tại trước khi sửa.
  4. Không hiện thẻ duyệt cho tool đọc.
- **Test:** pytest kiểm nội dung thẻ không chứa chuỗi nào từ câu trả lời của model; E2E `qr-pay.spec.ts` hoặc spec mới chụp thẻ có cảnh báo người nhận mới; test outbox kiểm email có số tiền và tên người nhận.

### T8 · Cách ly nguồn và bậc phản ứng (QĐ11, bước 1.14, 1.37)

- **File:** `backend/app/agent/quarantine.py`; `agent_access.py`; outbox.
- **Việc:**
  1. Bảng `quarantined_sources(source_id, owner_id, reason, rule_id, created_at, released_at)`. `source_id` có dạng `tool:record_id`, ví dụ `tx:TX-ABC` hoặc `ticket:TKT-1`.
  2. Khi classifier gắn cờ một nguồn, hoặc một luật `deny_and_flag` có nguồn kèm theo: ghi nguồn vào bảng.
  3. Tool đọc bỏ các bản ghi đã bị cách ly, thay bằng `{"quarantined": true}`.
  4. Khi gặp `deny_and_flag`: hủy run (`cancel_run`), từ chối mọi đề xuất đang chờ, gửi một thông báo cho user qua outbox.
  5. Nhân viên có quyền `support:write` xem và gỡ cách ly (route mới, nhớ thêm vào `route_matrix.json`).
- **Test:** cùng một memo độc, lần thứ hai không còn tới được model; customer không gỡ cách ly được; thông báo được gửi đúng một lần.

### T9 · Datamarking (QĐ2, bước 1.18)

- **File:** `agent_service/main.py`; cờ `spotlighting` từ T5 (truyền qua context của run).
- **Việc:** với trường UNTRUSTED, thay khoảng trắng bằng một ký tự đánh dấu sinh ngẫu nhiên cho mỗi run, chọn từ một dải Unicode ít gặp. Thêm câu hướng dẫn trong system prompt nói ký tự đó nghĩa là gì. Vẫn giữ thẻ `<untrusted_tool_data>`. Chỉ áp cho trường chữ, không áp cho số tiền hay mã.
- **Test:** ký tự đánh dấu khác nhau giữa hai run; trường số không bị đổi; tắt cờ thì đầu ra giống hệt hiện tại.
- **Đo thêm:** chạy 20 task lành trên mỗi model, xem benign utility có giảm không, rồi ghi số vào PR.

### T10 · Tầng classifier Prompt Guard 2 (QĐ6)

- **Việc người làm trước:** chấp nhận giấy phép Llama trên Hugging Face và tải model về máy lab. Agent không tự làm bước này.
- **File:** `backend/app/guard/promptguard.py`; nối vào chỗ gọi `classify`.
- **Việc:**
  1. Nạp model một lần khi khởi động. Nếu không có model thì tầng này báo `unavailable` và gateway DENY theo nguyên tắc chặn khi lỗi. Ngoại lệ: cấu hình A và C tắt tầng classifier.
  2. Thứ tự tín hiệu: regex → Prompt Guard 2 86M → classifier `qwen` hiện có. Mỗi tầng ghi một sự kiện `classifier_signal`.
  3. Bộ dữ liệu `research/data/vi_injection.jsonl`: payload tiếng Việt có dấu và không dấu cho 13 kênh, cùng số câu lành tương đương. Nhóm research viết payload, agent viết khung và bộ chấm.
  4. Script so 3 bộ phát hiện (Prompt Guard 2 gốc, bản fine-tune tiếng Việt có sẵn trên Hugging Face, classifier `qwen`), tính precision và recall trên bộ dữ liệu đó.
- **Xong khi:** có bảng precision/recall cho 3 bộ phát hiện, trên payload tiếng Việt.

### T11 · Dual LLM cho admin agent khi đọc ticket (QĐ10)

> **Cần người quyết định trước khi bắt đầu.** QĐ10 trong thiết kế nói admin agent chỉ đọc. Code hiện tại đã có 6 tool `propose_*`, có nhân viên duyệt. Đề xuất: giữ các đề xuất có duyệt, vì người duyệt đóng vai trò cắt chân thứ ba của Rule of Two. Chỉ thêm Dual LLM cho phần đọc ticket. Sau khi chốt, cập nhật QĐ10 trong doc.

- **File:** `backend/app/staff_tools.py`; module mới `backend/app/agent/quarantined_llm.py`.
- **Việc:**
  1. `read_ticket` không trả văn bản ticket cho LLM chính nữa. Văn bản đi qua một LLM cách ly (`llama3.2:3b`) với đầu ra ép theo JSON Schema: `category` (enum), `urgency` (enum), `mentions_instruction` (bool), `summary` (≤ 200 ký tự, không link, không markdown).
  2. Đầu ra sai schema thì bỏ và trả `{"unreadable": true}`.
  3. `summary` chỉ hiển thị cho nhân viên trong giao diện. Không đưa vào ngữ cảnh của LLM chính.
  4. `propose_ticket_reply`: nội dung trả lời do LLM chính viết dựa trên enum và dữ liệu có cấu trúc, không dựa trên văn bản ticket.
- **Test:** ticket chứa lệnh "đóng băng ACC-BOB-001" không làm LLM chính sinh ra `propose_account_status`; đầu ra sai schema bị bỏ; nhân viên vẫn thấy được ticket gốc trên màn hình.

### T12 · Đánh giá: model là biến, kẻ tấn công thích nghi, 4 cấu hình (QĐ12)

- **File:** `tools/live_attack/`, `research/`, `scripts/week8-report.py`.
- **Việc:**
  1. **Kênh:**
     - Mỗi kênh trong 13 nguồn có một hàm tiêm payload vào app đang chạy. Ví dụ: chuyển khoản đến có memo, QR có `add_info` và `to_name`, nickname, merchant, ticket, tài liệu RAG bản nháp, lịch sử hội thoại.
     - Thêm hai kênh trực tiếp: **chat một lượt** và **chat nhiều lượt**. Mentor tấn công bằng chat trực tiếp nhiều lượt hôm 14/11, nên kênh này bắt buộc phải có.
     - Bộ case cố định `research/cases/mentor-2026-11-14/` từ T0 luôn chạy trong mọi lần đo, làm bộ so sánh "trước và sau".
  2. **Kẻ tấn công thích nghi:** một LLM tấn công biết luật chính sách (giả định Kerckhoffs). Nó nhận phản hồi của lần thử trước (lớp nào chặn, `rule_id` nào) và sửa payload. Thử tối đa N = 10 lần. Báo ASR sau 1 lần và sau 10 lần.
  3. **Ma trận đo:** 4 cấu hình × 2 model (`qwen2.5:7b`, `qwen3:8b`) × các kênh × 6 mục tiêu (G1–G6). Mỗi lần chạy ghi digest model, phiên bản Ollama, commit.
  4. **Số liệu:** benign utility, utility under attack, L1/L2/L3 đọc từ `security_events` (T1).
  5. **Báo cáo:** bảng chính là L1 và L3 theo cấu hình. Bảng phụ tách theo kênh và theo model.
- **Xong khi:** có `docs/release/week8/RESULTS.md` với bảng số và lệnh tái hiện. Câu trả lời cho câu hỏi "ở C, L1 > 0 và L3 ≈ 0 không?" là có hoặc không, kèm số liệu.

### T13 · Tài liệu và gói evidence

- Cập nhật cột "Hiện trạng" trong doc thiết kế theo `DESIGN_STATUS.md` (T0) và các PR đã merge.
- Cập nhật `THREAT_MODEL.md` và `RBAC_MATRIX.md` theo T3, T8, T11.
- `docs/release/week8-evidence/`: CSV, bảng ASR, ảnh thẻ duyệt, GIF một ca bị chặn ở C, ghi chú các lần thử thất bại.

---

## 5. Checklist cho mỗi PR

- [ ] Tên nhánh `week8/tN-<ngắn>`; mô tả PR có link tới task trong file này.
- [ ] Có test đỏ trước, xanh sau; có positive control.
- [ ] Số test pass trước và sau (pytest, research, components, e2e nếu có).
- [ ] `ruff` sạch.
- [ ] Route mới có trong `route_matrix.json`; migration có version mới.
- [ ] Lớp mới bật/tắt được qua `layer_enabled`.
- [ ] Không log OTP, mật khẩu, token; không ghi vào DB demo.
- [ ] Ghi chú khác biệt giữa code thực tế và doc thiết kế, nếu có.

---

## 6. Các quyết định cần người chốt

| # | Câu hỏi | Đề xuất | Chặn task |
|---|---|---|---|
| 1 | Admin agent giữ hay bỏ các tool `propose_*`? | Giữ, có duyệt; thêm Dual LLM cho phần đọc | T11 |
| 2 | Thời gian chờ cho người nhận mới dài bao lâu? | Nhóm chọn một con số và ghi vào file chính sách | T6 |
| 3 | Ngưỡng điểm cho từng dải rủi ro | Đặt tạm, chỉnh sau khi chạy 100 task lành | T6 |
| 4 | Ai viết payload tiếng Việt và payload cho kẻ tấn công thích nghi? | Hai bạn research | T10, T12 |
| 5 | Model thứ hai | `qwen3:8b`, tắt thinking khi gọi tool | T12 |
| 6 | Nếu buổi họp tới diễn ra trước khi Phần I xong thì sao? | Kéo C1 và C2 lên chạy ngay sau T4. Các task này dùng lại bảng sự kiện (T1) và phần kiểm nguồn tham số (T3) | C1, C2 |
| 7 | Có cho phép AI đọc số tài khoản và số dư của chính user không? | Có, nhưng chỉ của chính user và chỉ khi user hỏi; luôn che số tài khoản của người khác | C2 |

---

# Phần II · Việc để đáp ứng yêu cầu của mentor (sau khi Phần I xong)

Phần II dùng lại nền của Phần I: bảng sự kiện (T1), nhãn nguồn (T3), chính sách JSON (T5), runner đo (T12). Mỗi task C vẫn tuân theo quy tắc ở mục 2 và checklist ở mục 5.

### C1 · Khóa chặt hành động: tạo tài khoản và chuyển tiền

- **Mục tiêu:** cả 3 case của mentor đều bị chặn khi gateway bật, có test hồi quy.
- **Việc:**
  1. Với mỗi đường code tìm được ở T0 việc 4: thêm kiểm tra phân quyền tại đó. Nếu là route hoặc tool không đi qua gateway, đưa nó vào `execute_tool` hoặc tắt nó.
  2. Không có tool nào của agent được tạo user hay tài khoản. Nếu staff thật sự cần, chỉ cho làm qua `propose_*` có duyệt, với quyền `settings:write`.
  3. Đường legacy chỉ chạy được trong pytest. Ngoài pytest phải trả 404 (kiểm lại cờ `LEGACY_AGENT_TEST_MODE`).
  4. Chạy lại toàn bộ bộ case `mentor-2026-11-14` ở cấu hình D. Mục tiêu L3 = 0 cho cả 3 case.
- **Test:** mỗi case của mentor có một test pytest. Các test này đỏ trên commit trước khi sửa và xanh sau khi sửa. Có positive control: chuyển tiền hợp lệ qua agent vẫn tới được thẻ duyệt.

### C2 · Chặn rò dữ liệu: quyền tối thiểu với dữ liệu

- **Mục tiêu:** AI không để lộ thông tin của user khác, và không để lộ số tài khoản hay số dư khi user không hỏi.
- **Việc:**
  1. Kiểm từng tool đọc: truy vấn có lọc `owner_id` không. Staff chỉ thấy đúng phạm vi vai trò của mình trong `RBAC_MATRIX.md`.
  2. Che dữ liệu theo trường trước khi đưa vào ngữ cảnh: số tài khoản của người khác chỉ hiện 4 số cuối; không đưa email, số điện thoại, `owner_id` vào ngữ cảnh nếu tool không cần.
  3. Bộ lọc đầu ra: thêm luật chặn khi câu trả lời chứa số tài khoản đầy đủ hoặc số dư của một tài khoản không thuộc user. Ghi sự kiện `output_filtered`.
  4. Thêm mục tiêu "rò dữ liệu" vào T12, gồm cả kiểu tấn công nhiều lượt dụ AI đọc dần từng phần dữ liệu.
- **Test:** customer hỏi số dư của user khác thì bị từ chối ở gateway và ở bộ lọc; staff vai trò support không thấy số dư; tấn công nhiều lượt không lấy được số tài khoản đầy đủ.

### C3 · Hoàn thiện chống quishing

- **Đọc trước:** `docs/research/QUISHING.md`, `research/quishing.py`, `backend/app/routes_qr.py`, `local_qr.py`, `vietqr.py`.
- **Việc:**
  1. QR chỉ được chứa dữ liệu thanh toán. Chuỗi URL hay dạng lệnh trong `add_info` hoặc `to_name` bị loại bỏ và gắn cờ.
  2. QR của ngân hàng ngoài: luôn hiện cảnh báo người nhận mới trên thẻ duyệt (nối với T6 và T7).
  3. QR từ ảnh tải lên: hiện rõ "dữ liệu này đến từ QR" trên màn hình xác nhận. Agent không được tự mở URL lấy từ QR.
  4. Demo hai ca: QR thật đi được tới OTP; QR độc bị chặn hoặc bị cảnh báo, kèm log.
- **Test:** E2E `qr-pay.spec.ts` thêm ca QR độc; pytest cho bước làm sạch `add_info`.

### C4 · MFA: xác minh và demo

- **Việc:**
  1. Kiểm tra luồng MFA trong code (PIN/TOTP, `mfa.py`, `mfa_settings.py`, `sessions.py`) có thực sự bật trong cấu hình demo không. Mentor ghi là "chưa có MFA", nên cần biết vì sao: chưa bật, chưa demo, hay thiếu thật.
  2. Nếu thiếu: bật TOTP khi đăng nhập và step-up khi chuyển tiền tới người nhận mới.
  3. Quay GIF luồng: đăng nhập → nhập TOTP → chuyển tiền tới người nhận mới → step-up → OTP.
- **Test:** E2E cho luồng MFA; pytest kiểm chuyển tiền tới người nhận mới không có step-up thì bị từ chối.

### C5 · Bộ kiểm thử API

- **Việc:**
  1. Từ `docs/release/openapi.json`: với mỗi route nhạy cảm, viết test cho các ca sau:
     - không có token
     - token của user khác (IDOR)
     - sai vai trò
     - tham số sai kiểu hoặc quá dài
     - gọi lại cùng request (replay)
     - gọi trực tiếp route của agent mà không có token uỷ quyền
  2. Dùng pytest với `TestClient`. Có thể thêm Schemathesis để sinh ca tự động từ OpenAPI nếu kịp.
  3. Xuất bảng "route → ca test → kết quả" vào `docs/release/week8/API_TESTS.md`. Gắn ảnh chụp Caido của 2–3 ca tiêu biểu.
- **Xong khi:** mọi route trong `route_matrix.json` có ít nhất ca không có token và ca sai chủ.

### C6 · Dữ liệu test giống thật và thêm chức năng

- **Việc:**
  1. Script `scripts/seed_realistic.py`: khoảng 50 customer với tên tiếng Việt, 2–3 tài khoản mỗi người, vài tháng giao dịch, người nhận đã lưu, thẻ, hóa đơn, ticket. Dùng seed cố định để tái hiện được. Không ghi đè DB demo.
  2. Có thêm vài nhân viên cho mỗi vai trò.
  3. Chạy lại bộ đo T12 trên dữ liệu mới, xem kết quả có giữ không.
- **Thêm chức năng:** chọn 1–2 chức năng mentor có thể thử với AI, ví dụ chuyển tiền định kỳ hoặc đổi hạn mức. Mỗi chức năng mới phải đi qua gateway như các tool khác. Ghi lựa chọn vào mục 6 trước khi làm.

### C7 · Gói bằng chứng cho buổi họp

- `docs/release/week8-evidence/`, gồm:
  - bảng trước/sau cho 3 case của mentor và cho tấn công nhiều lượt;
  - kết quả 4 cấu hình;
  - GIF quishing, GIF MFA;
  - bảng test API;
  - các lần thử thất bại.
- Một slide trả lời câu hỏi chính của mentor: *gateway chặn hành động trái phép và rò dữ liệu như thế nào, và bằng chứng test ở đâu*. Dùng sơ đồ kiến trúc 5 lớp. Mentor đang hiểu gateway là "một cái cờ", nên slide phải cho thấy các lớp kiểm tra thật bên trong.
- Chạy thử demo một lần từ đầu tới cuối với gateway bật.

---

## 7. Đối chiếu yêu cầu của mentor (14/11) với task

| Yêu cầu của mentor | Task |
|---|---|
| Chặn AI tạo tài khoản và chuyển tiền khi chưa được phép | T0 (tái hiện), T3, T4, T5, **C1** |
| Chặn AI để lộ thông tin user, số tài khoản, số dư | T3, **C2** |
| Chạy lại tấn công prompt injection và nhiều lượt, ghi kết quả | T0 (trước), T12 (sau), C7 |
| Hoàn thiện chống quishing | T7 (thẻ duyệt), **C3** |
| Thêm MFA | **C4** |
| Kiểm thử API | **C5** |
| Mở rộng chức năng và dữ liệu test | **C6** |
| Bằng chứng: demo trực tiếp, trước/sau, các lần thử thất bại | T0, T12, T13, **C7** |

**Thứ tự toàn bộ:** T0 → T1 → làn A (T2 → T3 → T4 → T5 → T6 → T8) song song làn B (T7, T9, T10, T11) → T12 → T13 → C1 → C2 → (C3, C4, C5, C6 song song) → C7.