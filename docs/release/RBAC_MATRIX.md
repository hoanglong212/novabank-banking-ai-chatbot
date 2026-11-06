# Week 7 — quyền staff và công cụ AI

Nguồn chuẩn: `backend/app/auth.py::ROLE_PERMISSIONS`, `staff_tools.py`, `agent/agent_access.py`, `backend/tests/route_matrix.json`.

| Role | Quyền app | Công cụ AI |
|---|---|---|
| customer | `banking:own`, `notifications:own` | Đọc dữ liệu của mình; đề xuất transfer/ticket/bill/card đúng intent; không có staff tools |
| support | `support:read`, `support:write`, `notifications:own` | `list_tickets`, `read_ticket`, `search_knowledge` |
| operations | `admin:transactions:read`, `admin:audit:read`, `notifications:own` | `list_transactions`, `search_knowledge` |
| auditor | như operations | `list_transactions`, `search_knowledge`; không đọc nội dung ticket |
| admin | như operations, thêm `settings:write`, `support:read`, `support:write` | `list_tickets`, `read_ticket`, `get_user_count`, `list_transactions`, `search_knowledge` |

Staff assistant dùng chung endpoints conversation/run có kiểm tra ownership, giao diện `/admin/assistant`. Endpoint approvals và banking cá nhân vẫn chỉ customer. Mọi thay đổi role trong matrix được kiểm tra bằng `test_SEC_01`; role không được lấy từ prompt hoặc model arguments.

`get_user_count` chỉ trả số tổng, không liệt kê danh tính. `list_transactions` trả ID giao dịch, số tiền, chiều, trạng thái, ngày; không trả account, holder hoặc description. `mask=false` bị từ chối. `read_ticket` yêu cầu ID có trong yêu cầu staff; nội dung được coi là dữ liệu không tin cậy, được source guard kiểm tra ở defended. Staff không có công cụ ghi, dù payload yêu cầu transfer.

Quyền bị từ chối được ghi trong `agent_calls` và `tool_events` dưới `ROLE_NOT_PERMITTED`. HTTP tool endpoint trả một envelope quyết định `DENY` như các tool hiện có; permission exception được chuyển thành audit event, không bỏ qua logging.

Kiểm thử: 11 tổ hợp role/tool, ticket injection, owner-only approval detail và toàn bộ forbidden route-role pairs. Live mock admin đọc số user qua service riêng đã được xác minh bằng Chromium. Từ khóa “act as admin” không nâng quyền; một prompt chứa chỉ dẫn bị guard chặn có thể bị từ chối cả khi người dùng là admin.
