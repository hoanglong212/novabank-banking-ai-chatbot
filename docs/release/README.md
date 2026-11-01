# Hồ sơ bàn giao NovaBank

Đọc [trạng thái nghiệm thu](STATUS.md) và [kết quả kiểm thử theo PDF mới](acceptance-audit/REPORT_VI.md) trước. Bản local hoạt động nhưng chưa đáp ứng toàn bộ 121 ca; bảng dưới là tài liệu triển khai trước lượt audit. Phát hành ngoài máy không thuộc phạm vi người dùng đã chốt. Các báo cáo vẫn giữ giới hạn kiểm chứng và cảnh báo dependency.

| # | Tài liệu |
|---|---|
| 1 | [SRS và 25 use cases](SRS.md) |
| 2 | [ERD và kiến trúc](ERD.md) |
| 3 | [Business rules](BUSINESS_RULES.md) |
| 4 | [Threat model](THREAT_MODEL.md) |
| 5 | [API specification](API_SPEC.md), [OpenAPI JSON](openapi.json) |
| 6 | [User guide](USER_GUIDE.md) |
| 7 | [Admin guide](ADMIN_GUIDE.md) |
| 8 | [Deployment, backup và restore](DEPLOYMENT.md) |
| 9 | [Test plan](TEST_PLAN.md) |
| 10 | [Prompt Injection Test Plan](PI_TEST_PLAN.md) |
| 11 | [Prompt Injection Results](PI_RESULTS.md) |
| 12 | [Security Evaluation](SECURITY_EVALUATION.md), [PDF](Security-Evaluation.pdf) |

Tài liệu bảo vệ: [10 slide HTML](Defense-Slides.html), [speaker notes](SLIDE_NOTES.md), [video demo có phụ đề](media/NovaBank-demo.mp4), [kịch bản demo](DEMO.md).

Dữ liệu thực nghiệm: [CSV](research/metrics.csv), [summary](research/summary.json), [dataset](research/dataset.json), [raw results nén](research/raw-results.zip), [ASR chart](research/asr.svg), [case đối chiếu](research/comparison.html). Toàn bộ dùng dữ liệu tổng hợp.
