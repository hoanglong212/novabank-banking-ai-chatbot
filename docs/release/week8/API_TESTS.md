# API authorization test evidence

Run `5abe8fe0f7f040318a1eb9b5bba505ac`. Matrix routes: 128. Observations: 580. Statuses: {'not_applicable': 128, 'passed': 452}. Matrix drift: False.

All resources are from disposable TestClient databases. Tests use real authentication, TOTP setup, new-payee step-up and email OTP to create the owned receipt. No live/demo database was changed. Resource-negative cases target existing Alice-owned records using Bob credentials; they are not missing-ID or invalid-DTO stand-ins.

| Method | Route | Scope | Anonymous | Cross-owner selector | Forbidden roles | Type/bounds |
|---|---|---|---|---|---|---|
| GET | `/openapi.json` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| HEAD | `/openapi.json` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/docs` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| HEAD | `/docs` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/docs/oauth2-redirect` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| HEAD | `/docs/oauth2-redirect` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/redoc` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| HEAD | `/redoc` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/api/customer/notification-preferences` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| PUT | `/api/customer/notification-preferences` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| POST | `/api/customer/beneficiaries/lookup` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | PASS 422 |
| GET | `/api/customer/profile` | own-or-approved-knowledge | PASS 401 | PASS 200 | NOT RUN | NOT RUN |
| POST | `/api/customer/profile/change` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| GET | `/api/customer/accounts` | own | PASS 401 | PASS 200 | PASS 403 | NOT RUN |
| PATCH | `/api/customer/accounts/{account_id}` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| GET | `/api/customer/beneficiaries` | own | PASS 401 | PASS 200 | PASS 403 | NOT RUN |
| POST | `/api/customer/beneficiaries` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | PASS 422 |
| DELETE | `/api/customer/beneficiaries/{beneficiary_id}` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| POST | `/api/actions/confirm` | own-or-approved-knowledge | PASS 401 | PASS 404 | NOT RUN | PASS 422 |
| GET | `/api/products/{kind}` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | NOT RUN |
| POST | `/api/products/actions` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| GET | `/api/insights` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | NOT RUN |
| PUT | `/api/insights/budgets` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | PASS 422 |
| PATCH | `/api/transactions/{transaction_id}/category` | own | PASS 401 | PASS 404 | PASS 403 | N/A: No typed JSON body; authorization/query cases apply |
| GET | `/api/statements.{fmt}` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | NOT RUN |
| GET | `/api/savings-goals` | own | PASS 401 | PASS 200 | PASS 403 | NOT RUN |
| POST | `/api/savings-goals` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | PASS 422 |
| PUT | `/api/savings-goals/{goal_id}` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| DELETE | `/api/savings-goals/{goal_id}` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| PATCH | `/api/bills/{bill_id}/saved` | own | PASS 401 | PASS 404 | PASS 403 | N/A: No typed JSON body; authorization/query cases apply |
| GET | `/api/support/tickets` | owner-or-support | PASS 401 | PASS 200 | PASS 403 | NOT RUN |
| POST | `/api/support/tickets` | owner-or-support | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| GET | `/api/support/tickets/{ticket_id}` | owner-or-support | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| POST | `/api/support/tickets/{ticket_id}/messages` | owner-or-support | PASS 401 | PASS 404 | NOT RUN | PASS 422 |
| PATCH | `/api/support/tickets/{ticket_id}` | owner-or-support | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| POST | `/api/support/tickets/{ticket_id}/attachments` | owner-or-support | PASS 401 | PASS 404 | NOT RUN | PASS 422 |
| GET | `/api/support/attachments/{attachment_id}` | owner-or-support | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| GET | `/api/admin/overview` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/admin/users` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| PATCH | `/api/admin/users/{user_id}` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| GET | `/api/admin/accounts` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| PATCH | `/api/admin/accounts/{account_id}` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| GET | `/api/admin/settings` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| PATCH | `/api/admin/settings` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| POST | `/api/admin/reconcile` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | N/A: No typed JSON body; authorization/query cases apply |
| GET | `/api/admin/audit` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| POST | `/api/qr/decode` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | PASS 422 |
| GET | `/api/knowledge` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| GET | `/api/knowledge/search` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| GET | `/api/knowledge/{document_id}` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| POST | `/api/admin/knowledge` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| PUT | `/api/admin/knowledge/{document_id}` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| POST | `/api/admin/knowledge-index` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | N/A: No typed JSON body; authorization/query cases apply |
| POST | `/api/agent/runs` | own | PASS 401 | PASS 404 | NOT RUN | PASS 422 |
| GET | `/api/agent/context` | run-owner-session | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 401 | NOT RUN |
| POST | `/api/agent/tools` | run-owner-session | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 401 | PASS 422 |
| POST | `/api/agent/finish` | run-owner-session | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 401 | PASS 422 |
| GET | `/api/agent/runs` | own | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| GET | `/api/agent/runs/{run_id}` | own | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| GET | `/api/agent/approvals` | own | PASS 401 | PASS 200 | PASS 403 | NOT RUN |
| POST | `/api/agent/approvals/{approval_id}` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| POST | `/api/conversations/{conversation_id}/stream` | own | PASS 401 | PASS 404 | NOT RUN | PASS 422 |
| GET | `/api/research/runs` | sandbox-enabled | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/research/runs/{run_id}` | sandbox-enabled | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/research/runs/{run_id}/cases` | sandbox-enabled | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/research/runs/{run_id}/export/{filename}` | sandbox-enabled | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| POST | `/api/research/runs` | sandbox-enabled | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| GET | `/api/health` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/api/ready` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/api/me` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| POST | `/api/transfers` | own | PASS 401 | PASS 400 | PASS 403 | PASS 422 |
| POST | `/api/transfers/{transfer_id}/otp` | own | PASS 401 | PASS 404 | PASS 403 | N/A: No typed JSON body; authorization/query cases apply |
| GET | `/api/transfers/{transfer_id}` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| POST | `/api/transfers/{transfer_id}/confirm` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| GET | `/api/vietqr/banks` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | NOT RUN |
| POST | `/api/vietqr` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | PASS 403 | PASS 422 |
| GET | `/api/conversations` | own | PASS 401 | PASS 200 | NOT RUN | NOT RUN |
| POST | `/api/conversations` | own | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| DELETE | `/api/conversations/{conversation_id}` | own | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| GET | `/api/conversations/{conversation_id}/messages` | own | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| GET | `/api/conversations/{conversation_id}/tool-events` | own | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| POST | `/api/conversations/{conversation_id}/messages` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| POST | `/api/conversations/{conversation_id}/demo/tool-check` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| GET | `/api/transactions` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| GET | `/api/transactions/{transaction_id}` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| GET | `/api/transactions/{transaction_id}/receipt.pdf` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| GET | `/api/notifications` | own-or-approved-knowledge | PASS 401 | PASS 200 | NOT RUN | NOT RUN |
| GET | `/api/announcements` | public-bank-news | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| PATCH | `/api/notifications/{notification_id}/read` | own-or-approved-knowledge | PASS 401 | PASS 404 | NOT RUN | N/A: No typed JSON body; authorization/query cases apply |
| POST | `/api/notifications/read-all` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | N/A: No typed JSON body; authorization/query cases apply |
| GET | `/api/admin/transactions` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/admin/transfers/{transfer_id}/audit` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| POST | `/api/auth/register` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/resend-verification` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/verify-email` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/forgot-password` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/reset-password` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/login` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/mfa/verify` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/mfa/email` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/auth/refresh` | public | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| GET | `/api/auth/sessions` | own-or-approved-knowledge | PASS 401 | PASS 200 | NOT RUN | NOT RUN |
| DELETE | `/api/auth/sessions/{session_id}` | own-or-approved-knowledge | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| POST | `/api/auth/logout` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | N/A: No typed JSON body; authorization/query cases apply |
| POST | `/api/auth/activity` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | N/A: No typed JSON body; authorization/query cases apply |
| GET | `/api/auth/login-history` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| GET | `/api/auth/mfa` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| POST | `/api/auth/pin` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| POST | `/api/auth/mfa/setup` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| POST | `/api/auth/mfa/enable` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| POST | `/api/auth/mfa/disable-request` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| POST | `/api/auth/mfa/disable` | own-or-approved-knowledge | PASS 401 | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | PASS 422 |
| PATCH | `/api/customer/beneficiaries/{beneficiary_id}` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |
| POST | `/api/agent/preview` | run-owner-session | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 401 | PASS 422 |
| POST | `/api/agent/runs/{run_id}/cancel` | own | PASS 401 | PASS 404 | NOT RUN | N/A: No typed JSON body; authorization/query cases apply |
| MOUNT | `` | compiled-frontend-only | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: Global/public or privileged staff surface; role checks apply instead | NOT RUN | NOT RUN |
| POST | `/api/dev/outbox/challenge` | login-challenge | N/A: Public/static/challenge-authenticated surface, not bearer protected | N/A: No caller-selected owned resource; authenticated identity is server-derived or approved knowledge is shared | NOT RUN | NOT RUN |
| GET | `/api/dev/outbox` | own | PASS 401 | PASS 200 | NOT RUN | NOT RUN |
| GET | `/api/dev/outbox/{message_id}` | own | PASS 401 | PASS 404 | NOT RUN | NOT RUN |
| GET | `/api/agent/approvals/{approval_id}` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| GET | `/api/admin/agent-gateway` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| PUT | `/api/admin/agent-gateway` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| GET | `/api/admin/agent-gateway/log` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/admin/agent-gateway/log.csv` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| GET | `/api/agent/quarantine` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | NOT RUN |
| POST | `/api/agent/quarantine/{source_id}/release` | staff | PASS 401 | N/A: Global/public or privileged staff surface; role checks apply instead | PASS 403 | PASS 422 |
| GET | `/api/transfers/{transfer_id}/step-up` | own | PASS 401 | PASS 404 | PASS 403 | NOT RUN |
| POST | `/api/transfers/{transfer_id}/step-up` | own | PASS 401 | PASS 404 | PASS 403 | PASS 422 |

## Additional verified controls

- Ordinary bank JWTs cannot call delegated-only endpoints. A Bob delegation cannot select an Alice run via a query or read her balance through tool arguments; Bob own-balance positive control remains allowed.
- A completed transfer replay with the same key returns the original receipt, a different key is rejected, and balances do not change again.
- Otherwise-valid oversized account/ticket/message/run/preview bodies and a string instead of integer transfer amount are rejected with 422.
- Owner positive controls return 200 for real ticket, attachment, transfer, transaction, receipt, run, approval, conversation and outbox resources.

## Applicability and limits

- Public/static/login-challenge surfaces are not bearer-protected; public does not mean OTP/refresh tokens are unnecessary for credential-specific actions.
- Global staff/research resources have role boundaries rather than a customer owner. Shared approved knowledge also has no per-customer owner. These are explicit N/A for IDOR, not passing wrong-owner tests.
- Identity-derived routes without a resource selector have no cross-owner pointer. Read collections are additionally tested against injected owner_id/user_id query selectors. Write DTOs remain strict and are covered by type/mass-assignment tests.
- Replay is verified for money confirmation here; broader auth/MFA/action replay semantics are covered by existing session/MFA/product suites, not claimed as per-route replay coverage by this table.
- JSON field-type probes cover typed bodies; endpoints with no JSON DTO are N/A for that probe. The table does not claim every possible parameter/value or concurrency interleaving was explored.
- The original matrix was measured through TestClient. A later [actual Caido capture](CAPTURE_COMPLETION.md) on an isolated synthetic bank now demonstrates anonymous 401, customer-to-staff 403 and foreign-conversation 404, with two owner-positive 200 controls. Those three proxy cases do not reclassify all 452 matrix observations as Caido measurements. Original redacted HTTP examples remain TestClient evidence.
- The normal full backend suite, independent review and browser acceptance remain separate gates. No security guarantee follows from green tests.

## Bank and Agent additions at 0548e998e44c9fb5400ae9211ffdaf6cdf677074

Fourteen method/path rows were absent from the historical table. GET and HEAD are counted independently.

| Method | Path | Service | Observed |
|---|---|---|---|
| GET | `/docs` | Agent | PASS 405 |
| HEAD | `/docs` | Agent | PASS 405 |
| GET | `/docs/oauth2-redirect` | Agent | PASS 405 |
| HEAD | `/docs/oauth2-redirect` | Agent | PASS 405 |
| GET | `/health` | Agent | PASS 405 |
| GET | `/openapi.json` | Agent | PASS 405 |
| HEAD | `/openapi.json` | Agent | PASS 405 |
| GET | `/redoc` | Agent | PASS 405 |
| HEAD | `/redoc` | Agent | PASS 405 |
| POST | `/run` | Agent | PASS 405 |
| GET | `/api/documents` | Bank | PASS 405 |
| POST | `/api/documents` | Bank | PASS 405 |
| DELETE | `/api/documents/{document_id}` | Bank | PASS 405 |
| GET | `/api/documents/{document_id}` | Bank | PASS 405 |
