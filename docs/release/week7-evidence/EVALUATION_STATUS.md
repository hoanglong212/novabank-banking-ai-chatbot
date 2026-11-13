# Week 7 — bộ đo đã kết thúc

Cập nhật 06/11/2026, 00:06 (Asia/Saigon).

- Full Qwen: **2.070 lượt**, **96 lỗi**, 220 lượt không áp dụng.
- Chạy lại sau sửa: **150 lượt**, lỗi giảm **96 → 6** trên cùng các cặp scenario/profile/repetition.
- Cả **90 lỗi trace tiết kiệm đã hết**; còn 1 ROUND_LIMIT và 5 ANOMALOUS_SEQUENCE.
- Bộ đo và xuất báo cáo đã hoàn tất, không còn chờ chạy nền.

[Bảng đầy đủ](asr-table.md) · [So sánh sau sửa](postfix-regression/comparison.md) · [Tình trạng nghiệm thu](completion.md).

Ruff 0.14.3 và ESLint 9.39.1 đã được cài theo quyền người dùng cấp ngày 06/11/2026; cả hai kiểm tra lint đã cấu hình đều đạt.

Chưa nghiệm thu toàn bộ Week 7: còn capture Caido/VM, profile/log demo cũ và review độc lập.

## Bổ sung 06/11/2026 tối

- Gateway tắt/bật (research, Qwen): **1.350 lượt, 0 lỗi**. ASR naive 93/350, baseline 85/350, defended 0/350. [Chi tiết](GATEWAY_OFF_ON.md)
- Corpus khó trên app thật: **330 lượt, 0 lỗi**. Một tấn công RAG lọt defended 3/3. Đo lại sau sửa: **204 lượt, 0 lỗi**, tấn công đó còn 0/3. [Chi tiết](HARD_LIVE.md)
- Full run 2.070 lượt không thay đổi. Đọc kèm ghi chú về lỗi nhận diện chuyển tiền trong [KNOWN_FAILURES.md](KNOWN_FAILURES.md).
