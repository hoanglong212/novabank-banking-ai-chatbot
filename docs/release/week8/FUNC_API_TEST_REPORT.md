# Week 8 · API and functionality evidence

Application revision `0548e998e44c9fb5400ae9211ffdaf6cdf677074`. Bank and Agent expose 125 OpenAPI operations. The router inventory includes 17 additional framework methods and mounts. All 125 operations were exercised for unsupported methods; 112 protected routes also returned 401 without credentials. These counts measure the specified probes. Positive schema and business coverage are reported separately.

## Acceptance decisions

- API-04 accepts HTTP 400 or 422. Both reject invalid amounts before money moves; compare pre/post DB state.
- TD5 compares deterministic business records, excluding salted password_hash. Random credential material must continue to differ across seeds.
- FN-TX-08 is N/A until a customer cancel-draft route exists. Agent run cancellation is a different action.
- Security acceptance is pending independent real-model evidence. The four tracked positive assistant cases are a versioned corpus; equivalence with any prior untracked suite is unverified.

## API test cases and results

These recorded probes used a synthetic path parameter where needed. The method probe sent OPTIONS with no Origin and no body. Protected operations also received a request using their declared method with no token. Full GEN columns, roles, fixtures and limitations are in the [matrix](verify-evidence/inventory-matrix.csv) and [verification report](VERIFY_FUNC_API_REPORT.md).

| Service | Operation | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| Agent | GET `/health` | OPTIONS | 405 | PASS 405 | PASS |
| Agent | POST `/run` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/actions/confirm` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/accounts` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/admin/accounts/{account_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/agent-gateway` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PUT `/api/admin/agent-gateway` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/agent-gateway/log` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/agent-gateway/log.csv` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/audit` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/admin/knowledge` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/admin/knowledge-index` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PUT `/api/admin/knowledge/{document_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/overview` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/admin/reconcile` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/settings` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/admin/settings` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/transactions` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/transfers/{transfer_id}/audit` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/admin/users` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/admin/users/{user_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/agent/approvals` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/agent/approvals/{approval_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/approvals/{approval_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/agent/context` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/finish` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/preview` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/agent/quarantine` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/quarantine/{source_id}/release` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/agent/runs` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/runs` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/agent/runs/{run_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/runs/{run_id}/cancel` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/agent/tools` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/announcements` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/activity` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/forgot-password` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | POST `/api/auth/login` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | GET `/api/auth/login-history` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/logout` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/auth/mfa` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/mfa/disable` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/mfa/disable-request` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/mfa/email` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | POST `/api/auth/mfa/enable` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/mfa/setup` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/mfa/verify` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | POST `/api/auth/pin` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/refresh` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | POST `/api/auth/register` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | POST `/api/auth/resend-verification` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | POST `/api/auth/reset-password` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | GET `/api/auth/sessions` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | DELETE `/api/auth/sessions/{session_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/auth/verify-email` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | PATCH `/api/bills/{bill_id}/saved` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/conversations` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/conversations` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | DELETE `/api/conversations/{conversation_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/conversations/{conversation_id}/demo/tool-check` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/conversations/{conversation_id}/messages` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/conversations/{conversation_id}/messages` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/conversations/{conversation_id}/stream` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/conversations/{conversation_id}/tool-events` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/customer/accounts` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/customer/accounts/{account_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/customer/beneficiaries` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/customer/beneficiaries` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/customer/beneficiaries/lookup` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | DELETE `/api/customer/beneficiaries/{beneficiary_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/customer/beneficiaries/{beneficiary_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/customer/notification-preferences` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PUT `/api/customer/notification-preferences` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/customer/profile` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/customer/profile/change` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/dev/outbox` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/dev/outbox/challenge` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | GET `/api/dev/outbox/{message_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/documents` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/documents` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | DELETE `/api/documents/{document_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/documents/{document_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/health` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | GET `/api/insights` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PUT `/api/insights/budgets` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/knowledge` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/knowledge/search` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/knowledge/{document_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/me` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/notifications` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/notifications/read-all` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/notifications/{notification_id}/read` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/products/actions` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/products/{kind}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/qr/decode` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/ready` | OPTIONS | 405 | PASS 405 | PASS |
| Bank | GET `/api/research/runs` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/research/runs` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/research/runs/{run_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/research/runs/{run_id}/cases` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/research/runs/{run_id}/export/{filename}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/savings-goals` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/savings-goals` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | DELETE `/api/savings-goals/{goal_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PUT `/api/savings-goals/{goal_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/statements.{fmt}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/support/attachments/{attachment_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/support/tickets` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/support/tickets` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/support/tickets/{ticket_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/support/tickets/{ticket_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/support/tickets/{ticket_id}/attachments` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/support/tickets/{ticket_id}/messages` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/transactions` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/transactions/{transaction_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | PATCH `/api/transactions/{transaction_id}/category` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/transactions/{transaction_id}/receipt.pdf` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/transfers` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/transfers/{transfer_id}` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/transfers/{transfer_id}/confirm` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/transfers/{transfer_id}/otp` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/transfers/{transfer_id}/step-up` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/transfers/{transfer_id}/step-up` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | POST `/api/vietqr` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |
| Bank | GET `/api/vietqr/banks` | OPTIONS; declared method without credentials | 405 / 401 | PASS 405; PASS 401 | PASS |

## Documented failed attempts

The original strict API-04 oracle required 400 and rejected six valid FastAPI 422 responses. The accepted outcomes now include both rejection codes and require unchanged balances. The first independent RAG run reported 19/20 display and 16/20 structured answers. In A, the contract lacked a duration but the answer suggested 36 months. The before/after report and the recorded JUnit failures remain available for comparison.

[Original independent results](VERIFY_FUNC_API_REPORT.md) · [Baseline artifact provenance](verify-evidence/baseline-manifest.json) · [Live RAG observations](verify-evidence/rag-results.json)

The remote branches and pull-request heads at the audited revision contain no historical positives.py or positives2.py objects. The versioned four-case corpus in verify/ is a replacement; its results cannot be compared as if they were the missing historical suite.
