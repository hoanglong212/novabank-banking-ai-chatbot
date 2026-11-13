# Qwen — đối chiếu sau sửa trace

So sánh đúng 150 cặp scenario/profile/repetition, không ghép số liệu này vào full run cũ. Đây là subset chọn theo lỗi đã thấy, không phải ước lượng độc lập cho toàn bộ bộ thử.

| Chỉ số | Trước sửa | Sau sửa |
|---|---:|---:|
| Số lượt | 150 | 150 |
| Lỗi thực thi | 96 | 6 |
| Tool utility thành công | 40 | 90 |

## Phân loại lỗi

| Nguyên nhân | Trước sửa | Sau sửa |
|---|---:|---:|
| ANOMALOUS_SEQUENCE | 5 | 5 |
| ROUND_LIMIT | 1 | 1 |
| UPSTREAM_ERROR | 90 | 0 |

Utility ở đây yêu cầu đúng tool/argument của corpus, không chấm ý nghĩa câu trả lời. Một câu trả lời hữu ích dùng tool khác có thể không đạt chỉ số này. Các lần chạy dùng temperature 0 và không gọi confirm payment.
