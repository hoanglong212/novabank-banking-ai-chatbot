# Threat model

Tài sản: phiên người dùng, OTP/TOTP seed, PII, số dư/ledger, lịch sử và audit, knowledge, tool authority, dữ liệu nghiên cứu. Đối thủ kiểm soát text customer hoặc nguồn thấp quyền, không được giả định kiểm soát JWT secret hay host OS.

| Nhóm | Ví dụ | Kiểm soát / bằng chứng | Rủi ro còn lại |
|---|---|---|---|
| Spoofing | Token khác user, delegate gọi confirm | JWT issuer/audience/session/version, MFA, owner queries; agent boundary tests | Máy khách/host bị chiếm vẫn ngoài ranh giới demo |
| Tampering | Đổi amount/recipient sau review, QR sửa | Server-stored payload, intent binding, OTP purpose/session, HMAC QR | Public demo credentials cần lớp hạn chế truy cập |
| Repudiation | Gửi lại tiền hoặc sửa lịch sử | Idempotency, immutable journal/snapshot, append audit | Audit chưa WORM ngoài host; admin OS có thể thay DB |
| Information disclosure | Đọc Bob, rò PII/token trong trace | Ownership, bounded DTO, pseudonym vault mã hóa, trace redaction, no-store | sessionStorage chịu rủi ro XSS; name recognition có giới hạn |
| Denial of service | Tool loop, body/file lớn, inference treo | Rate limits, 4 MiB body, file bound, 8 calls/120s, kill switch | Chưa load test nhiều người dùng/GPU scheduling |
| Elevation | Ticket/RAG giả mạo system, agent execute | Service riêng, narrow grant, human approval + OTP, D1–D10 | LLM và classifier không phải security boundary đáng tin tuyệt đối |

## Các nguồn injection

Direct prompt, transfer memo, beneficiary nickname, support ticket, RAG document, tool/API response và memory context. Dữ liệu giữ nguyên cho nghiên cứu, gắn trust/provenance và render escaped. Chỉ approved + published knowledge vào retrieval ứng dụng. Lab thay nguồn bằng fixture trong DB nghiên cứu riêng.

## D1–D10 trong ứng dụng và lab

| Lớp | Ứng dụng | Lab |
|---|---|---|
| D1 System rules | Prompt authority và cấm tiết lộ/đổi task | Toggle prompt |
| D2 Delimiters | untrusted_tool_data | Toggle source delimiter |
| D3 Least privilege | Read-own + write theo trusted user intent | Oracle expected-tool allowlist, giới hạn phải báo cáo |
| D4 Argument binding | Server parse latest request, strict DTO + owner | Deterministic expected-argument checks |
| D5 Human approval | Proposal owner/session, OTP riêng | Pending proposal, chỉ naive thực thi tiền giả |
| D6 Budget | Calls/round/time/body/quota | Calls/time cap |
| D7 Screening | Rules + local model, fail-closed source quarantine | Local classifier trước model chính, cache |
| D8 Output filter | URL/secret/canary filter trước final text | Canary/URL/fee evaluator |
| D9 Anomaly stop | Hai DENY dừng tool chain + admin kill switch | Dừng sau DENY trong chuỗi thí nghiệm |
| D10 Memory/data | Owner-bound conversation, encrypted vault, trace mask | Foreign-owner memory removal, masked trace |

Naive chỉ tồn tại ở lab. Baseline ứng dụng vẫn giữ authorization/intent binding/approval, mạnh hơn baseline lab. Kết quả lab không thể dùng như benchmark tuyệt đối của deployment.

## Web và vận hành

CSP banking app chỉ script self; tài liệu Swagger/ReDoc có ngoại lệ CDN + inline initializer riêng. CORS whitelist; auth dùng Authorization nên không có cookie auth để đặt Secure/HttpOnly/SameSite, cũng không có quyền dựa cookie bị CSRF. Điều này không loại bỏ XSS. HTTPS do Caddy; review gateway basic auth chặn truy cập công khai bằng credential demo. Agent container không có volume DB/JWT key. Backup được mã hóa, key tách archive; host access vẫn là quyền cao.

Dependency advisories, giới hạn kiểm thử và kết quả thực nghiệm nằm trong [Security Evaluation](SECURITY_EVALUATION.md). Chưa có pentest hay review độc lập.
