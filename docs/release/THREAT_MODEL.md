# Week8 threat model update (2026-11-15)

This section describes the current integrated implementation. The Week7 text below is preserved as historical context; its on/off profiles and D1-D10 lab mapping are not the Week8 A-D evaluation.

| Boundary | Current bank-owned control | Remaining limit |
|---|---|---|
| Tool authority | Required signed role, tool/intent/capability claims and independent hashes; DB ownership and current sessions; agent can propose, never confirm money movement | Host secrets and OS compromise are outside the demo boundary |
| Untrusted sources | Reviewed field registry, source screening, irreversible context taint, inherited provenance and critical-argument binding | Lexical source matching does not prove semantic intent; no claim of an original 13-channel match |
| Policy | Strict A-D JSON rules, rule reasons, unknown/invalid policy denial; weaker configurations only in scoped expiring lab sessions | Model and classifier behavior remains probabilistic |
| Risk and approval | Risk/cooling state, frozen bank templates, owner/session approval, audit and per-action OTP | Human approval can still be socially engineered; UI warnings are not authorization |
| Output | Field minimization, approved KB citations and canonical current balance rendering; restore aliases before the final disclosure check | Unsolicited credit-debt gap found in scoped review; final fix verification tracked separately |
| QR/OCR | Decode validates payment prose; URLs/instructions rejected without opening them; origin and external/new-payee warnings | Client-declared origin is not proof of capture; recipient trust is derived independently by the bank |
| New payee | Bank-derived recipient history; TOTP proof bound to session/factor/draft followed by distinct email OTP; atomic, idempotent posting | A valid user may authorize an unwanted payment; no automatic model posting |
| Quarantine/tickets | Persistent source quarantine and run revocation; staff review/release; dual-LLM assessment isolated from main model as constrained enums, human-only summary storage | Prompt Guard unavailable fails closed and may block benign sources; human reviewers remain necessary |
| Datamarking | Random per-run Unicode marker on reviewed untrusted text fields, unchanged IDs/numbers, deterministic removal of only that run marker before display | Narrow extraction utility evidence is not a general bank utility benchmark |
| Evaluation/seed | Disposable DB path guards, synthetic-only seed manifest, read-only copy source; deterministic synthetic business data with ledger checks | Production-like distribution is not real customer data; no performance/load assurance |

The scoped independent review found and rechecked a post-filter nested-alias disclosure fix, and reported an unsolicited credit-debt minimization gap. See [review scope and findings](week8/INDEPENDENT_REVIEW.md). This is not an external pentest or a claim of complete defect absence.

The exact Qwen3 model and Prompt Guard 2 model/runtime remain unavailable. Existing Qwen2.5/Llama measurements are supplemental, not substitutes. Configuration C smoke results with zero strict L1/L2/L3 outcomes cannot establish a positive vulnerable-model baseline. Current release results must distinguish unavailable, unexposed and failed trials from passes.

## Historical Week7 threat model

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

Dependency advisories, giới hạn kiểm thử và kết quả thực nghiệm nằm trong [Security Evaluation](SECURITY_EVALUATION.md). Historical Week7 statement: no independent review or pentest had been completed at that time; see the Week8 update above.
