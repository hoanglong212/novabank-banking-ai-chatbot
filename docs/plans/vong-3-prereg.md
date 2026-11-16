# R2 — đăng ký trước (preregistration)

Kế hoạch gốc: [vong-3-agent.md](vong-3-agent.md). File này không sửa sau khi
bắt đầu đo; nếu buộc phải sửa thì tạo bản mới và ghi lý do.

## SNAPSHOT (Bước 0c)

**SNAPSHOT = `6729f604873e660f1bf0c0e636948097898b80fb`** (nhánh `week8/r2-snapshot`).
Mọi lượt đo A/B/C/D của R2 phải dùng đúng commit này; không sửa code app trong lúc đo.

| Commit | Nội dung |
|---|---|
| `2684290` | 0a — tham số nhạy cảm phải xuất phát từ lời user (`PARAM_NOT_FROM_USER`, `T4-bind`) |
| `0422db3` | 0b — scaffold M-TRANSFER dùng tài khoản seed thật, không còn `W8_` |
| `fea80bb` | Proxy: override temperature/seed cho model trả lời chính, **mặc định tắt**, chỉ bật khi harness truyền `sampling` |
| `ed28b8e` | Utility harness: `--config B\|C\|D` |
| `6729f60` | 4 test cập nhật: assert cả `reason == 'PARAM_NOT_FROM_USER'` và `rule_id == 'T4-bind'` |

Kiểm tra tại snapshot (16/11/2026):

- Backend: **861 passed, 2 skipped, 1 xfailed, 0 failed** (335,64 s). Một cảnh báo
  khóa JWT ngắn thuộc test cố ý tạo JWT giả.
- Research: **60 passed, 0 failed**. Ruff sạch.

Môi trường đã ghi nhận:

- Model: `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`,
  Ollama riêng `127.0.0.1:11435`, `OLLAMA_MODELS=D:\Ollama\models`. Không tải model.
- Seed tổng hợp: `D:/NovaBank-Week8-Lab/source-current/.local/week8-seed/bank.sqlite3`,
  SHA-256 `68fa158f9d0643a3e6f67a4e96444f1622d54c6163e0a1053132ffb694b2e208` (trùng R1).

SHA-256 các file harness tại snapshot:

| File | SHA-256 |
|---|---|
| `research/r2_protocol.py` | `62615d76dc1b1c2b513038971b9caecba2edac08274a13315c2a664f6eb34d24` |
| `research/week8_proxy.py` | `d4f87c0b3fe4ed41157bbb0e912ee54573deca9e34a77336817fb668ab49052f` |
| `research/week8_runtime.py` | `bbda8f7d9b96a37321a997e496ed94df46949145279b7cf323cc23ddc307695b` |
| `research/promptguard_utility.py` | `b55ee33df14d25477b0b8a65bf81671f31422def9a6b83dc01e75214cb322a3a` |

## Các mục Bước 1 còn lại

Chưa điền: danh sách payload, số lần thử, seed, định nghĩa chỉ số (L1/L2/L3,
L1-answer) và quy tắc dừng. Phải bổ sung và commit trước lượt đo đầu tiên.
Chưa có lượt đo R2 nào chạy.
