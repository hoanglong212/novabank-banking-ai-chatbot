# Week 7 — bộ đo đã kết thúc

Cập nhật 06/11/2026, 00:06 (Asia/Saigon).

- Full Qwen: **2.070 lượt**, **96 lỗi**, 220 lượt không áp dụng.
- Chạy lại sau sửa: **150 lượt**, lỗi giảm **96 → 6** trên cùng các cặp scenario/profile/repetition.
- Cả **90 lỗi trace tiết kiệm đã hết**; còn 1 ROUND_LIMIT và 5 ANOMALOUS_SEQUENCE.
- Bộ đo và xuất báo cáo đã hoàn tất, không còn chờ chạy nền.

[Bảng đầy đủ](asr-table.md) · [So sánh sau sửa](postfix-regression/comparison.md) · [Tình trạng nghiệm thu](completion.md).

Ruff 0.14.3 và ESLint 9.39.1 đã được cài theo quyền người dùng cấp ngày 06/11/2026; cả hai kiểm tra lint đã cấu hình đều đạt.

Chưa nghiệm thu toàn bộ Week 7: còn capture Caido/VM, profile/log demo cũ và review độc lập.
