# Tiến độ Tuần 7 (nhánh `week7/fix-outbox-profile-gateway`, không push)

Quy tắc mỗi commit: `pytest` toàn bộ backend + test `research/` + `ruff` + typecheck frontend đều pass; xfail tái hiện R1 vẫn là xfail. Lệnh (từ gốc repo):

```bash
cd backend && .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
backend/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider research/tests
backend/.venv/Scripts/python.exe -m ruff check backend/app agent_service research scripts tools
cd frontend && npx --no-install tsc -p tsconfig.app.json --noEmit
cd frontend && npx playwright test        # e2e, chạy lại sau các thay đổi frontend
```

Tổng kết dùng cho slide: `docs/release/week7-evidence/WEEK7_SUMMARY.md`.

## Trạng thái theo mục

| Mục | Trạng thái | Commit | Ghi chú |
|---|---|---|---|
| 1a. Commit phần đang dở sau e2e | ✅ | `5658d9d` | Playwright 41/41 (9,9 phút) |
| 1b. Kiểm tra origin của opener, rate limit challenge | ✅ | `504c735` | Không có kênh `postMessage`; giới hạn 600 lần / 15 phút / IP |
| 1c. Test không tool agent nào đọc được `dev_outbox` | ✅ | `917771f` | Chạy thật 32 tool, có trace SQL; bản đột biến làm cả 2 test fail |
| 1d. `OUTBOX_TAKEOVER.md`: bảng trước/sau và 3 biến thể | ✅ | `cc01813` | Chuỗi tấn công dừng ở bước 2 (`401`) |
| 1e. `gateway_compare.py` với Qwen thật, phiên đo | ✅ | `8ee5983` | OFF 8/16 (trước 9/16), ON 0/16; chênh lệch đã giải thích |
| 1f. KNOWN_FAILURES, BAO-CAO R1–R3, runbook demo | ✅ | `5e03ce4` | `docs/release/DEMO_RUNBOOK_WEEK7.md` |
| 2. B5: token có chữ ký, tách khoá, HMAC OTP | ✅ | `adbca6e`, `e13b970` | 19 test token, 4 test khoá; e2e 41/41 sau thay đổi |
| 3. RBAC_MATRIX và test leo quyền qua `propose_*` | ✅ | `d2c6b58` | 30 test |
| 4. Vector hoá đơn PDF → RAG | ➖ **nhóm tự phụ trách, dự kiến Tuần 8** | — | Claude không làm phần này. Đã có số liệu cho cùng payload ở dạng văn bản (xem "Chưa xong") |
| 5a. Utility under attack và chạy lại off/on | ✅ | `c1dc06b`, `aa26697` | 1.350 lượt Qwen, 0 lỗi |
| 5b. Ánh xạ 6 case direct công khai | ⚠️ một phần | `edeedd1` | Repo không có danh sách 6 case; đã kiểm kê mọi kịch bản `direct` |
| 5c. Chú thích `asr-table.md` | ✅ | `e2f59a1` | |
| 6. Chạy LAN và runbook Caido | ✅ | `0529f94` | Đã kiểm tra qua IP LAN: health 200, UI 200, outbox ẩn danh 401 |
| 7. `WEEK7_SUMMARY.md` và file này | ✅ | commit cuối | |

## Commit trên nhánh (cũ → mới)

| Commit | Nội dung |
|---|---|
| `c6c701f` | Tài liệu R1 và test tái hiện |
| `b2b9e1b` | R1: outbox theo user hoặc challenge |
| `4a4797d` | R2: server tự chọn profile |
| `9451ace` | R3: gateway OFF chỉ trong phiên đo |
| `504c735` | Kiểm tra origin của opener, rate limit challenge |
| `917771f` | Test không tool agent nào đọc được `dev_outbox` |
| `5658d9d` | E2E: đăng nhập qua tab hộp thư rồi chuyển tiền |
| `cc01813` | Bảng trước/sau R1 và 3 biến thể |
| `adbca6e` | Khoá theo mục đích, HMAC cho OTP chuyển tiền (R7, R8) |
| `8ee5983` | Đo lại gateway OFF/ON với Qwen bằng phiên đo |
| `5e03ce4` | BAO-CAO, KNOWN_FAILURES, runbook demo |
| `e13b970` | B5: token xác nhận chuyển tiền có chữ ký |
| `d2c6b58` | RBAC_MATRIX và test leo quyền qua `propose_*` |
| `c1dc06b` | Chỉ số utility under attack |
| `edeedd1` | Kiểm kê kịch bản direct (ánh xạ 6 case) |
| `e2f59a1` | Chú thích `asr-table.md` |
| `0529f94` | Lệnh LAN và runbook Caido |
| `aa26697` | Chạy lại lab off/on với đủ 3 chỉ số |

## Kết quả test cuối (14/11/2026, trước commit cuối)

- Backend: **671 passed, 1 xfailed, 1 warning** (xfail = `test_anonymous_outbox_takeover_chain`; warning = khoá HMAC 9 byte trong một test cũ).
- Research: **15 passed**.
- Ruff: **All checks passed**. Typecheck frontend (`tsc`): sạch. Component test (`npm run test:components`): pass.
- Playwright e2e: **41/41 passed** (lần chạy sau B5).

## Số liệu đo thật tuần này

| Phép đo | Lệnh | Kết quả | File |
|---|---|---|---|
| App thật, gateway OFF/ON | `tools/gateway_compare.py --base http://127.0.0.1:8086 --out docs/release/gateway-compare/2026-11-14-session` | OFF 8/16, ON 0/16 | `docs/release/gateway-compare/summary.md` |
| Lab, 3 profile | `python -m research.run --models qwen2.5:7b --corpus all --repetitions 5` | ASR naive 116/350, baseline 89/350, defended 0/350 | `docs/release/week7-evidence/offon-research-2026-11-14/README.md` |

Ollama chạy riêng trên `127.0.0.1:11435`, model có sẵn trong `D:\Ollama\models` (không tải gì); đã tắt sau khi đo. Daemon ở cổng 11434 của bạn không bị đụng tới.

## Chưa xong và vì sao

1. **Mục 4 – vector hoá đơn PDF → RAG: nhóm tự phụ trách, dự kiến Tuần 8.** Claude không làm phần này. Chưa có code nào của mục này trong repo. Cùng payload kiểu hoá đơn **ở dạng văn bản** (payload đầu tiên của `hard_attacks()`) đã được đo:
   - App thật, 14/11 (`hard-direct-01`): không lọt cả khi gateway tắt lẫn bật. Nguồn: `docs/release/week7-evidence/DIRECT_CASE_MAPPING.md`.
   - Lab, 14/11, 7 vector `hard-*-01`, mỗi profile 35 lượt: naive 8/35, baseline 0/35, defended 0/35 (judge cách ly 30/35). Nguồn: `docs/release/week7-evidence/offon-research-2026-11-14/observations.csv`.
2. **Mục 5b – ánh xạ 6 case công khai: một phần.** Không tìm thấy danh sách 6 case trong repo, nên cột "Case công khai" trong `DIRECT_CASE_MAPPING.md` để trống, không đoán.
3. **Caido/Burp:** chưa có capture thật (cần VM).

## Cần bạn quyết định hoặc tự làm

- **Mục 4 (Tuần 8, nhóm tự làm):** vector hoá đơn PDF → RAG. Kết quả nên đặt cạnh số liệu dạng văn bản ở trên để so sánh.
- **Mục 5b:** gửi danh sách 6 case direct injection công khai để điền ánh xạ.
- **Caido:** làm theo `docs/release/week7-evidence/capture/CAIDO_RUNBOOK.md`, lưu file vào `capture/caido/`, điền bảng "Kết quả thật".
- **Review rồi push nhánh** (mình không push). Lưu ý cho người review:
  - Hộp thư phải mở từ nút trong app.
  - Link xác minh và link reset giờ chỉ đọc bằng `scripts/dev-outbox.py`.
  - Khách hàng không còn chọn được `baseline`.
  - `/confirm` bắt buộc `confirm_token`: client nào gọi API trực tiếp phải lấy token từ response của draft.
- **Sau khi merge:** nếu deploy cố định, đặt 4 khoá trong `.env` (`JWT_SECRET`, `QR_SIGNING_KEY`, `OTP_HASH_KEY`, `TRANSFER_TOKEN_KEY`); để trống thì mỗi lần khởi động lại sẽ sinh khoá mới.
