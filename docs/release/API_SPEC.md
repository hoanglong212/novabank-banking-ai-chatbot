# API specification

OpenAPI sinh trực tiếp từ FastAPI tại [openapi.json](openapi.json). Khi chạy local, mở `/docs`, `/redoc`, `/openapi.json`. Schema là nguồn chính xác cho DTO, constraints và response status.

| Nhóm | API tiêu biểu | Quyền |
|---|---|---|
| Identity | `/api/auth/register`, `login`, `mfa/verify`, `refresh`, `logout` | Public lifecycle có quota; authenticated session khi cần |
| Sessions | `/api/auth/sessions`, MFA settings | Current owner/session, current password cho thay đổi bảo mật |
| Customer | `/api/customer/profile`, `profile/change`, `accounts`, `beneficiaries` | Customer own |
| Notifications | `GET/PUT /api/customer/notification-preferences` | Customer own; bill reminders/budget alerts only; security/money alerts stay on |
| Transfers | `/api/transfers`, `/{id}/otp`, `/{id}/confirm` | Customer own; confirm cần OTP và hỗ trợ Idempotency-Key |
| Products | `/api/products/{cards,bills,savings}`, `/api/actions/confirm` | Customer own; server-stored action challenge |
| History | `/api/transactions`, `/{id}`, `/{id}/receipt.pdf` | Owner; separate admin read routes |
| Planning | `/api/insights`, budgets, savings-goals, statements.pdf/csv | Owner, bounded query |
| Support | `/api/support/tickets` và reply/attachment/assignment | Owner hoặc support permissions; operations bị chặn GET danh sách; auditor không đọc nội dung ticket khách |
| Admin | `/api/admin/overview`, users/accounts/settings/reconcile/audit | Read permission hoặc settings:write |
| Knowledge | `/api/knowledge`, search, `/api/admin/knowledge-index` | Approved published for customers; edit admin |
| Agent | `/api/conversations/{id}/stream`, `/api/agent/runs` | Customer session |
| Tools | `/api/agent/context`, tools, preview, finish | Audience novabank-agent-tools, ai:read + ai:prepare; run bị hủy không dùng tiếp được |
| Approvals | `/api/agent/approvals/{id}` | Customer owner and originating session |
| Research | `/api/research/runs`, detail/cases/export/start | Chỉ admin và RESEARCH_SANDBOX_ENABLED=true |

Đợt sửa 01/11 bổ sung: POST `/api/customer/beneficiaries/lookup`, PATCH `/api/customer/beneficiaries/{id}`, GET danh bạ với `q`, POST `/api/agent/runs/{id}/cancel`. Filter transaction/agent gồm `from_date`, `to_date`, `recipient`. [Ma trận route đầy đủ](../../backend/tests/route_matrix.json) có test phát hiện route chưa khai báo. [Bằng chứng trước/sau](acceptance-fixes/REPORT_VI.md).

## Contract notes

- Bearer login JWT không dùng thay delegated JWT hoặc ngược lại. Agent không được gọi API confirm ngân hàng.
- 401 là phiên/grant không hợp lệ; 403 là thiếu quyền hoặc intent; nhiều owner lookup dùng 404 để không tiết lộ tồn tại; 409 là replay/state conflict; 422 là DTO; 429 là quota; 503 là dependency/DB/kill switch.
- `POST /api/transfers/{id}/confirm` nên giữ một `Idempotency-Key` cho mọi retry của cùng thao tác. Không tạo key mới sau timeout không biết trạng thái.
- SSE có events `run`, `progress`, `tool`, `complete`, `error`. Client chỉ render final answer đã kiểm duyệt, không render raw model tokens. Không dùng legacy `/messages` ở deployment: route này 409 trừ launcher regression riêng.
- Tên `vietqr` còn giữ để tương thích API/tool cũ nhưng chỉ tạo NovaBank QR nội bộ. Không có request mạng đến VietQR/NAPAS.
- API response chứa `demo_otp` ở transfer cho mô phỏng; product/email OTP đọc qua CLI outbox. Không dùng contract này cho tiền thật.
- `/api/health` là liveness. `/api/ready` kiểm tra local model và, khi `BANK_REQUIRE_AGENT=true`, agent health. Agent `/health` báo process/transport, không đảm bảo chất lượng suy luận.

Body cap 4 MiB và no-store áp dụng API. Header auth/OTP/password/refresh không được đưa vào request logs. Swagger documentation có CSP CDN riêng, banking frontend vẫn script self.
