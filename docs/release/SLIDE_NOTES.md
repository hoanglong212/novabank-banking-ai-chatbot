# Nội dung slide bảo vệ

Mở [Defense-Slides.html](Defense-Slides.html), dùng phím mũi tên hoặc Page Up/Page Down. Bản offline HTML có thể chỉnh source, không phải PPTX. Runtime xuất PowerPoint tích hợp không khả dụng trong phiên này.

## 1. NovaBank và prompt injection

Dữ liệu và tiền đều giả. Bản này phục vụ nghiên cứu, chưa là hệ thống ngân hàng production.

## 2. Phạm vi hệ thống

SRS.md ánh xạ từng use case với hành vi và điều kiện nghiệm thu.

## 3. Ranh giới thực thi

Agent không mount DB và không nhận signing key. Không có tool confirm.

## 4. Một đường ghi sổ cho mọi sản phẩm

SQLite write lock phù hợp stack demo. Không tuyên bố đã kiểm thử PostgreSQL hoặc hệ thống phân tán.

## 5. Nghiên cứu có kiểm soát

Nguồn truy xuất được đưa sẵn vào context. Mỗi mẫu đo một quyết định tool. Dataset v1.1 và hash nằm trong summary.json.

## 6. Các lớp phòng vệ

Classifier là defense in depth. Authorization và ledger phải an toàn ngay cả khi model hoặc classifier thất bại.

## 7. Kết quả trên corpus đã đo

Không có lỗi chạy, mọi sandbox journal cân. Utility = đúng tool/args. Một proposal sai được chấp nhận có thể tính attack success dù tiền chưa chuyển.

## 8. Cùng payload, hai kết quả

Stored observation beneficiary_nickname-01, qwen2.5:7b. Baseline vẫn cần human approval; đây chưa phải chuyển tiền trái phép.

## 9. Bằng chứng kiểm tra

Số test và command outcomes cuối cùng nằm trong STATUS.md và evidence/. Line coverage không phải branch coverage.

## 10. Giới hạn và phát hành

Nguồn: PI_RESULTS.md, SECURITY_EVALUATION.md, raw-results.zip. Không dùng demo cho tiền hoặc PII thật.