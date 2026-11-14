# C4 recipient-bound authenticator step-up

Existing MFA was real: password login already offers email verification or enrolled TOTP, transaction confirmation already supports TOTP/PIN, and codes burn their time step. Customer trusted-device sign-in can intentionally skip repeated login MFA; staff cannot. The missing control was an independent, fresh, exact-draft verification before paying a new recipient. This lane preserves existing factors for known payees, adds enrollment without a PIN fallback for unknown payees, and requires a separate email OTP after new-payee TOTP step-up.

## Files and contract

- `app/transfer_stepup.py`: migration18, status/verify/require helpers, bank-owned `verified_payees` and `transfer_stepups`. There is no public write route for payee trust.
- `routes_customer.py`: GET/POST `/api/transfers/{transfer_id}/step-up`, customer-only, owner/session-bound and no-cache. POST accepts only a strict six-digit `code`.
- `TransferStepUp.tsx` and the minimal `TransferSheet.tsx` wrapper: show new-recipient warning, existing password-checked authenticator enrollment, fresh-code proof, separate email-code request and final confirmation. QR/OCR origin is displayed only from the server-returned draft metadata.
- `tests/stepup_helpers.py`: explicit fixed synthetic known-payee entries for ordinary legacy regression scenarios. It does not intercept TokenClient, approve arbitrary drafts, alter balances or create transfer rows. Security tests explicitly clear fixture trust. The production registry accepts no customer writes; its real entries reference completed/settled bank transfers.

Proof is valid for at most120seconds, capped by draft expiry. It binds owner, current session, auth version, authenticator ciphertext fingerprint and frozen draft fields including amount, recipient, bank, name, source account and fee. Codes and TOTP secrets are never stored in the proof. Five failed attempts are bounded by the existing account lockout plus per-draft/session attempt window. A saved beneficiary, pending external payment, different session/draft/amount, expired proof or replaced authenticator does not satisfy step-up.

## Required root integration hooks

These shared files were deliberately not edited in this lane. Until these hooks are installed, standalone module tests pass but the bank transfer boundary is **not yet integrated**.

1. In `Database.initialize`, after migrations1–17:

```python
from .transfer_stepup import initialize as initialize_transfer_stepup
initialize_transfer_stepup(conn, now())  # reserved migration18
```

2. In `api/routes/transfers.py:create_transfer`, defer automatic OTP issuance for an unknown payee. Keep the prepared draft and signed confirmation token available for review:

```python
draft = await transfers.prepare(db, user, payload.model_dump(exclude_none=True))
from ... import transfer_stepup
with db.connect() as conn:
    needs_stepup = transfer_stepup.status(conn, user, draft)['required']
if not needs_stepup:
    draft, _ = transfers.issue_otp(db, user, draft['id'])
return with_token(draft)
```

3. In `transfers.issue_otp`, after `_own_transfer`/status checks and before generating/mailing any code, under its existing write transaction:

```python
from . import transfer_stepup
transfer_stepup.require_stepup(conn, user, t)
new_payee_email = transfer_stepup.email_confirmation_required(conn, user, t)
```

For the existing factor branch, use `elif not new_payee_email and (factor := transaction_factor(...)) in ('totp','pin')`; otherwise the existing emailed-OTP hash/outbox branch runs. Preserve the root's cooling-off guard and contextual email template.

4. In `transfers._confirm_locked`, preserve authenticated/idempotent cached receipt retrieval first. For a live pending draft, before OTP validation or money posting, call `require_stepup(conn,user,t)` again. This second guard is mandatory: guarding only `/otp` leaves a direct-confirm bypass. If `email_confirmation_required(conn,user,t)` is true, accept only the separately issued email hash (`otp_hash` must not be TOTP_MARK/PIN_MARK and must match `_otp_hash`). Do not fall through to `verify_factor` for a new-payee email challenge. For all other transfers preserve existing PIN/TOTP verification. An optional cached client field must never choose the factor.

5. After actual internal completion/status update, in the same posting transaction, call `transfer_stepup.remember_completed(conn, transfer_id)`. After external settlement succeeds/status updates, call the same helper in that settlement transaction. It returnsFalse for pending/failed transfers and has no public route. Migration18 imports only historical completed internal/settled external payees. Runtime `new_recipient` also consults authoritative completed history, so missing cache population cannot be confused with a user-added beneficiary.

6. Add these entries to `backend/tests/route_matrix.json` (C5 owns the consolidated matrix):

```json
{"method":"GET","path":"/api/transfers/{transfer_id}/step-up","roles":["customer"],"scope":"own"}
{"method":"POST","path":"/api/transfers/{transfer_id}/step-up","roles":["customer"],"scope":"own"}
```

Map `AUTHENTICATOR_ENROLLMENT_REQUIRED` to403 if desired; `STEP_UP_REQUIRED` is400 like other invalid transaction factors. UI calls the status/enrollment routes and does not bypass on an error. Preserve root's additional TransferSheet error messages when applying this patch.

## Validation and evidence

- Watched red: new module absent (5test setup errors); test fixture initially omitted typed `TransferArgs` defaults and was corrected before behavioral evaluation.
- Fresh core suite: **6passed** in the isolated worktree. Genuine TOTP success/benign known-payee controls, nonce replay, exact-draft binding, expiry, session mismatch, wrong owner/audience, failure limits, pending-payee non-trust and authenticator replacement are covered. No live demo database is touched.
- Frontend TypeScript/Vite build passed using a junction to existing dependencies; no dependency installation. Existing main-bundle size warning remains.
- New Playwright case is discovered successfully by `--list`. It must be run in the integrated root after the hooks and migration above, not claimed as passing from this lane. It exercises real TOTP enrollment/login, blocked pre-step-up OTP issue, fresh step-up and separate email OTP, and records five screenshots suitable for a GIF. Screenshots are taken with code inputs empty; no video is recorded so setup secrets/TOTP/email codes are not persisted as evidence.

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_transfer_stepup.py -q
cd frontend
npm run build
node node_modules/@playwright/test/cli.js test new-recipient-stepup.spec.ts --reporter=list
```

This lane has not independently reviewed the final root integration. It does not claim C4's full end-to-end/GIF acceptance until that integrated browser test passes. Rollback removes the new routes/UI and leaves additive migration18 tables unused; do not delete data or downgrade a live database.

## Follow-up read-only integration review

Root installed the migration, create/issue/confirm guards, separate email-factor selection, posting/settlement trust registration and two route-matrix entries. Read-only review confirmed that authenticated cached-receipt retrieval remains before fresh-proof checks and a live pending confirmation rechecks proof before money posting. Root additionally bound proof to memo content and source origin; the focused test now checks those fields too.

Added `test_direct_confirm_cannot_bypass_stepup_even_with_valid_bank_token_and_totp`: a real bank-signed confirmation token and genuinely correct transaction TOTP against a legacy TOTP challenge completed a10.000VND transfer on the pre-integration path (watched red: HTTP200/COMPLETED instead of STEP_UP_REQUIRED). Against the integrated root source, the same call is refused without spending the token or moving funds. Explicit step-up using that fresh code, then a separate emailed OTP completes exactly once; idempotent retry is stable and spent-token replay is409. This is a meaningful boundary regression, not a denial caused by a malformed token/wrong code.

Validation of the updated focused suite against integrated root application modules: **7passed**. Root source was read-only; all financial mutations were in pytest temporary databases. Full E2E/GIF remains separately scheduled by root.

`tests.stepup_helpers.seed_regression_payees(conn)` may be invoked once after TestClient startup in ordinary `conftest.client` and `acceptance_helpers.client` fixtures, and once in the disposable E2E launcher after initialization. Its finite Alice/Bob/Charlie recipient list is explicit. It must never be called from TokenClient.request, from a draft hook, from ordinary production startup, or for arbitrary newly registered customers. C4 security fixtures clear all `origin='fixture_known'` trust before testing; the C4 E2E case explicitly clears its target's trust and asserts no completed historical transfer. Registry entries reflect fixture starting state, not successful MFA. Do not count them as live security evidence.
