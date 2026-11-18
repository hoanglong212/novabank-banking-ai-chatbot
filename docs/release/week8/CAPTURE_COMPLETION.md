# C3/C4/C7 capture follow-up

Delivered actual continuous MFA and quishing WebM/GIF recordings in [completion-captures](../week8-evidence/completion-captures/README.md). Final browser run: **3 passed in 63.28s, exit0**. Existing assertions were retained; only capture settings, secret-field visual masking and readable pauses were added to isolated test copies. No production app or existing test files were edited.

MFA records TOTP login → exact-recipient step-up → separate email OTP → posted receipt. Quishing retains hostile signed QR rejection and now includes a genuine QR reaching a distinct email OTP screen after recipient-bound TOTP verification, without confirming payment. The earlier legitimate-QR recording ending at transaction PIN remains available as historical evidence.

The additional C3 run passed **1 test in 31.91s, exit 0**; continuous video duration **17.88s**, original 1440×900 WebM plus 10fps/960px GIF. [OTP screenshot](../week8-evidence/completion-captures/04-genuine-qr-email-otp.png) and [machine-readable acceptance](../week8-evidence/completion-captures/quishing-genuine-email-otp.json) show `otp_method=email`, one new transfer OTP, unchanged 10,000,000 VND balance and zero confirmation requests. Visual inspection verified the source warning, recipient proof and email-OTP screen; the setup seed was outside the recorded context and secret fields were masked.

The baseline regression fixture marks this synthetic recipient as known. The continuation removes only that marker from its own disposable DB before startup, then executes real enrollment/login/recipient verification. It uses an ephemeral port and an isolated state directory, so it does not overwrite the standard E2E `latest.json`. All 498 application/build/helper hashes remained unchanged through capture. Port 64520 stopped during fixture cleanup. Original application/test files and the prior blocked/genuine recordings were preserved.

Reproduce using existing installed tools, from repository root:

```powershell
backend/.venv/Scripts/python.exe .local/week8-completion/captures/prepare.py
```

From `frontend`:

```powershell
$env:NO_COLOR = $null
node node_modules/@playwright/test/cli.js test --config ../.local/week8-completion/captures/playwright.config.ts
```

From repository root:

```powershell
backend/.venv/Scripts/python.exe .local/week8-completion/captures/export_recordings.py
```

The separate C3 continuation was prepared with `backend/.venv/Scripts/python.exe .local/week8-completion/captures/prepare_qr_otp.py`, run from `frontend` with `node node_modules/@playwright/test/cli.js test --config ../.local/week8-completion/captures/qr-otp/playwright.config.ts`, and exported using `.local/week8-completion/captures/export_qr_otp.py`. Its own logs, JSON report and explicit exit code are under `.local/week8-completion/captures/qr-otp/`. The export refuses to replace an already published follow-up record. Independent final review belongs to the parent completion lane.

The first recording run passed3 but was too quick to inspect the intermediate verification screens comfortably. The next run added1.3s review holds; PowerShell treated an inherited NO_COLOR/FORCE_COLOR warning as native stderr. A final rerun removed NO_COLOR and explicitly recorded the child exit code0. All three runs' browser assertions passed; the final recordings replace only this lane's own prior exports.

Caido 0.59.1 is installed. After the user resolved its telemetry-choice screen, the agent observed the fresh workspace and created **Week8 API Captures** in the dedicated instance on 18080. The actual proxied checks passed **401 / 403 / 404**, with two owner-positive controls returning 200. Sessions were revoked and the disposable server stopped. Four original, visually inspected Caido screenshots now show all three paths/statuses and all three error bodies. Authenticated request headers remain outside the screenshot viewport; the raw proxy database is local only.

The capture completed at **2026-11-15T04:22:03Z**. [Result and source hashes](../week8-evidence/completion-captures/caido-api-checks.json) record 101 source/policy files, unchanged before/after the run. An initial reused-connection reset was resolved in the isolated harness by disabling HTTPX keep-alive reuse; the final command exited 0. Its screenshot filter selects only the successful run's port 60983. No production fix or dependency installation was needed.

With the isolated Caido project selected, reproduce from repository root:

```powershell
backend/.venv/Scripts/python.exe .local/week8-completion/captures/api_capture.py --execute
```

The guest project is temporary and Caido may delete it on its next startup. Released screenshots and JSON persist independently. The original stopped Caido instance on 8080 and all existing NovaBank deployments/databases remain untouched. This evidence establishes the stated acceptance paths and three API boundaries, not a claim that every possible defect is absent.

All files owned by this lane are under `.local/week8-completion/captures/`, `docs/release/week8-evidence/completion-captures/`, and this report. Existing user/database evidence is preserved. The C-configuration demo rejected by automatic safety review was not retried.
