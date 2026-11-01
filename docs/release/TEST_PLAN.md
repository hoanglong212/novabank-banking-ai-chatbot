# Test plan và bằng chứng nghiệm thu

**Cập nhật sau audit 01/11:** [bảng ca sửa, quyết định đặc tả và log](acceptance-fixes/REPORT_VI.md). Expectation chốt: AUTH-03=422 cho trường role/balance; ADM-03=phí khóa ở draft và hạn mức kiểm lại lúc confirm; AI-13=401 hoặc 403 nhưng không có tác dụng; NF-07=`12,500,000 VND`. SEC-01 theo [ma trận route](../../backend/tests/route_matrix.json). Kết quả mới: 271 pytest, 17 nhóm component, 15 E2E pass. AI-14/PI-05/PI-06 chưa chạy lại theo yêu cầu.

Các bài test dùng DB tạm. Không reset DB người dùng. `scripts/check-migrations.py` backup nguồn sang bản sao rồi migration, kiểm tra old-row projection, integrity và reconciliation, sau đó xác nhận source hash không đổi.

| Nhóm | Kiểm tra chính | Nguồn |
|---|---|---|
| Auth/session | Verify/reset/MFA/TOTP replay, logout/revoke, refresh rotation, idle/version | `backend/tests/test_*session*`, `test_*mfa*`, browser security/identity |
| Money | Posting atomic, concurrent confirm, insufficient funds, limits, cache mismatch, trigger immutable | `test_transfers.py`, `test_ledger.py` và regression tests |
| Products | OTP wrong owner/replay, duplicate bills, card freeze/purchase, credit repayment, maturity/early withdrawal | `test_customer_products.py`, `test_product_invariants.py` |
| Preferences | Owner isolation, optional alerts disabled, critical alerts retained; browser reload persists | `test_notification_preferences.py`, browser products flow |
| Settlement | Pending → completed/failed, fee refund, second worker no duplicate | `test_settlement.py` |
| Analytics | Fee included, refund excluded, savings interest included, CSV formula escaping | `test_release_boundaries.py`, `test_services.py`, product maturity test |
| Agent authority | Wrong audience, cross-owner read, logout revokes grant, approval owner, tool budget | `test_agent_boundary.py`, `test_release_boundaries.py` |
| Knowledge/source | Approved-only, stale embedding race, poisoned source quarantine | `test_release_boundaries.py`, isolated-model acceptance |
| Research evaluator | Real synthetic posting + balanced ledger, reset, forbidden directory, output filter | `test_research_invariants.py` |
| Frontend | Static component rendering, escaping, role navigation, refresh coordination, loan schedule | `frontend/tests/components.test.tsx`, `session.test.ts` |
| Browser | Alice–Bob 9 bước, responsive auth/history, recovery/MFA, products, support, logout/idle | 12 Playwright tests in `frontend/tests/e2e` |
| Real LLM/service | Balance, RAG, transfer proposal over two real HTTP processes | `scripts/check-agent-service.py` |
| Responsive/UI | 44 snapshots; 375/768/1440, every Explore service, admin, real SSE approval | `frontend/scripts/release-browser.mjs` |
| Recovery | Encrypted snapshot, 52 tables match, MFA key restored, overwrite refused | restore drill artifact |

## Lệnh tái chạy

```powershell
.\backend\.venv\Scripts\python.exe scripts/financial-coverage.py
cd frontend
npm run test:components
npm run test:e2e
```

Chạy model acceptance từ root bằng `backend/.venv/Scripts/python.exe scripts/check-agent-service.py`. Nó tự mở hai process tạm và đóng sau khi kiểm tra, không cài/pull gì. `release-browser.mjs` cần dedicated rich demo trên :8084 và agent :8094; script có comment/config chỉ rõ DB. Không trỏ script vào dữ liệu thực.

Financial coverage dùng `trace` chuẩn Python vì môi trường không có coverage/pytest-cov. Đo executed source lines, có thread tracing cho TestClient, không phải branch coverage. Chỉ gồm posting/transfers/ledger/products/settlement; không gọi đây là coverage toàn repo.

E2E regression dùng `LEGACY_AGENT_TEST_MODE=true` để giữ kiểm thử deterministic cũ; nó không chứng minh service separation hay LLM. Acceptance và browser release riêng đã thực hiện service/LLM thật. Mock không được tính vào 1.790 quan sát nghiên cứu.

## Chưa chứng nhận

Không có CI remote xanh cho diff hiện tại, review độc lập, Docker runtime, VPS/ACME, load test hoặc adversarial evaluation thích ứng. Test local xanh không đồng nghĩa production readiness. [STATUS](STATUS.md) chốt outcome và đường dẫn evidence, không ghi pass trước khi command hoàn tất.
