# QĐ6 — utility sau T10

Đo thực tế ngày 15/11/2026 trên `week8/integration`, nền `73dd661` cộng thay đổi
QĐ6 chưa commit tại thời điểm đo. [JSON đủ 100 dòng](../week8-evidence/qd6-r1/qd6-utility-100.json)
ghi hash từng file ứng dụng và seed; không chỉ dựa vào tên nhánh.

## Cấu hình và kết quả

- Cấu hình **D**, chuỗi regex → **Prompt Guard 2 bản gốc, ngưỡng 0.5** →
  **qwen2.5:7b**. Không bật bản fine-tune tiếng Việt.
- `GUARD_MODEL` có mặc định riêng `qwen2.5:7b`, không tự kế thừa model trả lời
  chính. PG cho qua vẫn phải chạy Qwen; thiếu detector vẫn chặn.
- Giữ nguyên ID, prompt và expected tool của bộ 100 task lịch sử. Bốn cohort
  25 task dùng bản sao database tổng hợp riêng; model chạy thật qua Ollama local.
- Runtime Torch/Transformers đã cài, CPU 4 thread, timeout PG 30 giây trong
  harness để tính cả lần nạp lạnh. Mặc định ứng dụng vẫn là 5 giây; kết quả này
  không chứng minh SLA nạp lạnh 5 giây hay thay thế kiểm tra triển khai.

| Lượt đo | Utility | Detector unavailable | Task PG chặn nhầm | Task đi qua PG |
|---|---:|---:|---:|---:|
| Lịch sử trước weights | 90/100 | 9 | Không đo được | Không đo được |
| T10 bản gốc / 0.01 | 97/100 | 0 | 3 | 10 |
| **QĐ6 bản gốc / 0.5 + Qwen2.5** | **100/100** | **0** | **0** | **10** |

Có **200 lời gọi model chính** trong lượt mới. Cả 100 dòng đều `measured`,
không bỏ lỗi/rerun để chọn kết quả. Cả bốn snapshot tiền/tài khoản/sản phẩm
không đổi; không gọi endpoint duyệt hay xác nhận thanh toán. Cả 10 task đọc
nguồn đều ghi đủ ba tầng `classifier_signal`, PG và Qwen cho qua. Có 11 lượt
sàng lọc nguồn trong 10 task (task thẻ đọc hai nguồn), không phải chỉ 10 lần
inference PG.

“Utility đạt” nghĩa là tool mong đợi có quyết định `ALLOW` (với thao tác ghi là
đề xuất), không phải chuyển tiền đã hoàn tất hay đánh giá chất lượng văn bản.
Tỷ lệ PG chặn nhầm quan sát được là **0/10 task có sàng lọc, 0/11 lượt sàng lọc**; không dùng
100 làm mẫu số để diễn giải FPR của PG. Mười nguồn tổng hợp là tập rất nhỏ,
không đủ kết luận không còn dương tính giả ngoài thực tế.

## Lý do và tái lập

Xem [QĐ6 trong thiết kế](../../thiet-ke-gateway.md#qđ6--bộ-phát-hiện-nguồn-sau-t10)
và [T10](T10_PROMPTGUARD_RESULTS.md). Dữ liệu T10 gợi ý dùng Qwen làm tín hiệu
chính cho tiếng Việt, tránh false block của bản fine-tune và ngưỡng PG 0.01.
Lượt này kiểm tra utility của cấu hình người dùng chọn, không hiệu chỉnh lại
ngưỡng trên dữ liệu tấn công và không chạy ma trận B/C/D.

```powershell
D:/NovaBank-Week8-Lab/runtime/Scripts/python.exe scripts/week8-promptguard-utility.py --project-root . --seed-db D:/NovaBank-Week8-Lab/source-current/.local/week8-seed/bank.sqlite3 --model-path models/prompt-guard-2-86m --threshold 0.5 --output .local/week8-evaluation/qd6-utility-05
```

Output phải là thư mục mới; lệnh từ chối ghi đè. Raw model logs và database có
dữ liệu xác thực thử nghiệm giữ trong `.local/`, không đưa lên Git. Không tải
model, không truy cập token Hugging Face, không thay DB/dịch vụ đang phục vụ app.
