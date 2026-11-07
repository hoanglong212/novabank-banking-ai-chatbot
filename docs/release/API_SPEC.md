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
- `/api/vietqr/banks` lấy danh sách ngân hàng công khai từ VietQR, có cache và giữ ngân hàng demo khi nguồn ngoài lỗi. `/api/vietqr` vẫn tạo QR NovaBank nội bộ; không gọi dịch vụ tạo mã hoặc chuyển tiền thật.
- API response chứa `demo_otp` ở transfer cho mô phỏng; product/email OTP đọc qua CLI outbox. Không dùng contract này cho tiền thật.
- `/api/health` là liveness. `/api/ready` kiểm tra local model và, khi `BANK_REQUIRE_AGENT=true`, agent health. Agent `/health` báo process/transport, không đảm bảo chất lượng suy luận.

Body cap 4 MiB và no-store áp dụng API. Header auth/OTP/password/refresh không được đưa vào request logs. Swagger documentation có CSP CDN riêng, banking frontend vẫn script self.

### Explore service updates (2026-11-08)

- `PUT /api/savings-goals/{goal_id}` accepts the same body as goal creation (`label`, `target_vnd`, `target_date`, optional `savings_id`). It requires ownership of the goal and any linked active savings account. Invalid calendar dates and blank names return 422; inactive savings links return 409.
- `GET /api/support/tickets` accepts optional `status=OPEN|IN_PROGRESS|RESOLVED|CLOSED`. Filtering applies before the count and pagination, preserving customer ownership and staff permissions.
- Beneficiary lookup/save accepts banks from the existing VietQR catalog. Other-bank account numbers must contain 6–19 digits; returned names explicitly say `SIMULATED RECIPIENT`. NovaBank continues to verify active internal account names locally.
### Admin Home dashboard (2026-11-08)

- `GET /api/admin/overview?days=7|30|90` defaults to 7; other values return 422. Existing overview fields remain available. `dashboard` adds period/previous-period metrics, a zero-filled daily series, current snapshots, recent transfers, bounded attention queues and recent banking events. Requires existing `admin:audit:read` permission.
- Period boundaries and daily grouping use Vietnam calendar dates and transfer confirmation time (creation fallback); effective outcome uses settlement status where present. OTP drafts are excluded. Settled volume counts each completed transfer principal once, excludes fees, and does not double-count internal account entries. Completion rate is completed / (completed + failed), or null without terminal outcomes.
- Snapshot counts are current, independent of selected period. Pending queue spans all dates; failed queue and recent transfers use selected period. Queues return at most 20 entries each, recent transfers 8, events 5. Counts may exceed displayed rows. Refresh is explicit; `updated_at` identifies the snapshot.
- The dashboard reuses `POST /api/admin/reconcile` with existing `settings:write` permission. No saved report is displayed as unchecked, never as healthy. No migration or external banking connection is introduced.
