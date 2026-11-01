# Kịch bản trình diễn và video

[Video MP4](media/NovaBank-demo.mp4) ghi màn hình Chromium thật trên dedicated synthetic DB. Có phụ đề tiếng Việt, không audio. Không dùng kết quả model giả hoặc dựng lại số dư. Profile/flow được gắn rõ trong nội dung.

| Đoạn | Thao tác / lời giải thích |
|---|---|
| Mở đầu | Alice đăng nhập MFA; Home hiển thị seed 6 tháng, đây là tiền giả |
| Chuyển tiền | Alice chuyển Bob 2 triệu; review người nhận/phí/OTP; confirmation và biên lai PDF |
| Sản phẩm | Analytics/budgets và debit/credit minh họa đường ghi sổ chung |
| AI | Conversation mới hỏi lãi savings, Qwen dùng RAG source; đề xuất 200.000 VND đến Bob |
| Human approval | UI hiển thị bank-owned status, không có tiền do agent thực thi; Alice Decline |
| Bob | MFA riêng và Alerts hiển thị tiền vào từ Alice |
| Nghiên cứu | Admin dashboard 1.790 observations, utility và giới hạn ASR |
| So sánh | Mở stored case baseline chấp nhận sai proposal vs defended chặn D7. Chưa có tiền chuyển ở baseline case này |
| Kết thúc | Giới hạn corpus, review/deploy/CI và evidence |

Nguồn quay có thể tái chạy: `frontend/scripts/record-demo.mjs`. Nó chỉ dành cho `.local/full-roadmap/rich-demo.sqlite3`, bank :8084, agent :8094. Cần frontend build và local models sẵn có. `scripts/seed-demo.py` tạo DB mới, không reset target có sẵn. Script ghi file dưới `.local/full-roadmap/video`, không tự upload video.

Số dư trong video khác fixture Alice–Bob E2E vì seed phong phú có lương/chi tiêu sáu tháng. Không dùng video để thay test số dư cụ thể 10 triệu → 8 triệu của E2E. Video đầu đã giúp phát hiện câu trả lời model sai về trạng thái approval; bản bàn giao được quay lại sau khi thêm bank-owned confirmation text.
