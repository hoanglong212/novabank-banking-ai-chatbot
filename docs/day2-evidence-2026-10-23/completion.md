# Kết quả triển khai — 23/10/2026

## Phạm vi hoàn thành

Đã xử lý năm mục trong phản hồi mới nhất và hoàn thành luồng chuyển tiền thủ công trên trình duyệt. Chưa hoàn thành toàn bộ MVP tuần.

1. **Fail closed:** định danh tài khoản sai, nhiều định danh hoặc placeholder không phân giải được trả yêu cầu làm rõ, không trả số dư mặc định. Ánh xạ placeholder là tham số nội bộ theo request. Sau phân giải vẫn kiểm tra quyền sở hữu; Alice hỏi tài khoản Bob bị từ chối. Chỉ dùng tài khoản phiên khi yêu cầu không nêu đích. Có 12 test riêng cho binding, gồm mapping số, mapping Bob, không tái sử dụng mapping và lịch sử chưa phân giải.
2. **Trình duyệt:** harness hiện có dùng Edge CDP, không dùng Playwright. Wrapper tự khởi động Vite/backend ở các cổng trống trên 127.0.0.1, dùng proxy cùng origin và APP_ORIGINS khớp. Đã sửa race khi chờ reload. Dừng đúng các server do test tạo và xóa DB tạm; không dừng Vite đang có của người dùng.
3. **PII điện thoại:** loại trừ chuỗi có ngữ cảnh số tiền liền kề, giữ nhận diện số điện thoại trong câu có ngữ cảnh gọi điện. 11 test phát triển và 12 câu đánh giá tổng hợp mới; đánh giá mới đạt 12/12, không chỉnh lại theo kết quả. Chi tiết trong phone-context.json. Đây là thử nghiệm recognizer, chưa phải tích hợp model/history; không thay thế số liệu đánh giá toàn bộ PII cũ.
4. **Quyết định trả lời:** model đề xuất tool; backend ràng buộc dữ liệu, kiểm tra quyền, chỉ thực thi một tác vụ mỗi lượt rồi dựng câu trả lời theo mẫu/FAQ. Không có lượt LLM thứ hai. Nội dung chuyển khoản tự do chỉ hiển thị ở giao diện ngân hàng, không xuất hiện trong kết quả tool của chatbot.
5. **Chuyển tiền:** API tài khoản/lịch sử, tạo intent, xem intent, confirm và cancel; UI xem trước/xác nhận/biên nhận/lịch sử. Intent có hạn 5 phút; dữ liệu được ràng buộc khi tạo. Confirm chỉ nhận payload rỗng, không cho đổi số tiền/người nhận. Debit, credit, transaction và audit cùng transaction SQLite BEGIN IMMEDIATE. Retry cùng intent trả cùng biên nhận. Hai intent khác nhau vẫn là hai yêu cầu chuyển tiền.

## Bằng chứng kiểm thử

| Lệnh (qua rtk proxy) | Kết quả |
| --- | --- |
| backend: `.\.venv\Scripts\python.exe -m pytest -q` | 99 passed, 52.33s |
| frontend: `npm run build` | Thành công |
| frontend: `npm run test:components` | 6 nhóm kiểm tra qua |
| frontend: `npm run test:identity` | Login/reload/isolation/logout và chuyển tiền qua; cleanup thành công |
| `git -c core.safecrlf=false diff --check` | Thành công trước cập nhật tài liệu cuối |

Kiểm thử transfer bao gồm xác nhận lặp, xác nhận đồng thời, không đủ tiền, hết hạn, CSRF, sở hữu, hủy intent và lỗi chèn giao dịch buộc rollback. Test đồng thời dùng hai intent 8 triệu với số dư 12,5 triệu: chỉ một lần debit thành công, số dư còn 4,5 triệu; replay trả cùng receipt.

Trình duyệt thực: Alice chuyển 100.000 VND cho Bob. Preview tồn tại sau reload; confirm cho số dư Alice 12.400.000 VND. Sau đổi phiên, Bob thấy 8.850.000 VND và lịch sử nhận tiền; không đọc được hội thoại Alice. Ảnh transfer-receipt.png đã được xem kiểm tra ở 1440×1000.

Các test dùng DB tạm và dữ liệu mô phỏng. Không reset DB demo, không in mật khẩu/JWT, không commit/push. Backend có một cảnh báo deprecation từ Starlette/httpx; build có cảnh báo Tailwind không tìm utility class, cả hai lệnh vẫn thành công.

## Giới hạn và việc kế tiếp

- Presidio chưa nằm trên mọi request model/history; ánh xạ mới là hợp đồng nội bộ đã được test. Chưa chạy lại toàn bộ benchmark PII nghiệp vụ sau tích hợp, không tuyên bố 11/18 ca hỏng cũ đã được giải quyết end-to-end.
- Không đo lại Ollama ở lượt này. Số liệu lần trước vẫn thuộc báo cáo ngày 1, không gán cho phiên bản mới.
- LangGraph, QR/camera/HTTPS trên thiết bị demo và gateway từ nhóm chưa tích hợp. Browser test dùng mock model.
- Parser định danh hỗ trợ cú pháp demo đã kiểm thử; chưa chứng minh bao phủ mọi cách diễn đạt ngôn ngữ tự nhiên.
- Independent review còn chờ; kết quả trên là kiểm thử và tự kiểm tra triển khai.

## Rollback

Sao lưu DB trước thay đổi triển khai. Bảng ngân hàng mới là bổ sung, không cần xóa để rollback mã nguồn. Chỉ revert các file thuộc thay đổi đã xem xét; bảo toàn dữ liệu/evidence và thay đổi khác trong working tree. Không chỉnh/xóa hàng loạt DB hoặc khôi phục token demo cũ trên dịch vụ công khai.
