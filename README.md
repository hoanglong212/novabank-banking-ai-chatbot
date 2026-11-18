# NovaBank Banking Web App + AI Agent

A banking simulation and prompt-injection research project. React 19/Vite/TypeScript/Tailwind, FastAPI/SQLite, and a separate HTTP agent. All accounts and money are fictional.

**Current handoff:** [implementation and verification status](docs/release/STATUS.md), [12-document dossier](docs/release/README.md), [25 use cases](docs/release/SRS.md), [security report PDF](docs/release/Security-Evaluation.pdf), [demo video](docs/release/media/NovaBank-demo.mp4), [defense slides](docs/release/Defense-Slides.html).

## Start the real Agent from a fresh clone

Start Docker Desktop or Docker Engine with Compose v2. From the repository root, run:

```sh
docker compose -f compose.local.yaml up -d --build
```

Compose builds the web app, starts the bank and isolated Agent, and downloads the models into a Docker volume. The first run needs internet access and roughly 7 GB for model weights in addition to the images. Allow time for the downloads and first CPU inference. Python, Node.js and a host Ollama install are unnecessary for this path.

1. Open <http://127.0.0.1:8080> and sign in as `alice` with password `Alice@2026`.
2. On the verification screen, open the demo inbox and enter the sign-in code in the form.
3. In **Assistant**, ask **What is my account balance?**

Use `docker compose -f compose.local.yaml logs models` to check download progress. Once running, [the readiness endpoint](http://127.0.0.1:8080/api/ready) should show `ready` and `llm_provider: ollama`. Stop with `docker compose -f compose.local.yaml down`. Both bank data and downloaded models persist. See [.env.example](.env.example) for the port and model overrides.

For a shared browser URL, one operator can run the same model stack on a team server with HTTPS and a reviewer network allowlist. Reviewers only need the URL, a browser and access to that network. See [deployment and troubleshooting](docs/release/DEPLOYMENT.md), including the optional licensed Prompt Guard runtime for reading untrusted sources.

### Native Windows development

With Python, Node.js and Ollama installed, pull `qwen2.5:7b` and `nomic-embed-text:latest`, then use the existing launcher:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Setup -Mode ollama
# On later runs:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Mode ollama
```

Open http://127.0.0.1:8080. The launcher builds the frontend and starts the bank plus isolated agent (:8093). Ctrl+C stops both. `-Mode mock` uses explicitly labeled deterministic responses without a model. The command does not install dependencies or pull models. See [deployment and configuration](docs/release/DEPLOYMENT.md).

Other synthetic logins include `bob / Bob@2026`, `charlie / Charlie@2026`, `support / Support@2026`, `operations / Operations@2026`, `auditor / Auditor@2026` and `admin / Admin@2026`. Staff logins always require email MFA or configured TOTP. Transfers always require OTP. Enter codes in the authentication form.

Public demo credentials require a restricted review environment. The supplied Compose/Caddy configuration includes an access gateway. Do not use real banking credentials or PII.

## Capabilities

- MFA, rotating refresh sessions, recovery, profile changes with current password and OTP.
- Double-entry transfers, locked fees, daily limits, idempotency, interbank pending/reversal, internal signed QR, receipts and alerts.
- Debit/credit simulation, bills, term savings, goals/calculators, monthly spending/budgets and PDF/CSV statements.
- Customer support with attachments/replies, role-based operations/admin, approved knowledge library.
- Isolated agent with short delegated grants, RAG citations, approval cards, streamed progress and persisted tool traces. No agent confirm authority.
- Resettable research sandbox, 35 attack scenarios/7 vectors, 100 legitimate tasks, two models, naive/baseline/defended profiles, D1-D10 ablations and results dashboard.

QR codes remain NovaBank-only, not NAPAS/VietQR. The bank directory is fetched from VietQR's public `/v2/banks` API and cached; cached/demo banks remain available during outages. Bank logos load from VietQR's image hosts. Personal QR generation stays local and does not call an external QR service. All transfers and email/SMS/KYC remain simulated. The Group 10 external gateway remains an adapter contract, not a verified integration.

## Verification

```powershell
.\backend\.venv\Scripts\python.exe scripts/financial-coverage.py
cd frontend
npm run test:components
npm run test:e2e
```

CI runs these checks and a container smoke test with a real model. To verify a fresh demo with the default model, run `python scripts/smoke-agent.py --balance`.

Measured research: 1,790 observations, zero execution errors, balanced sandbox journals. Defended utility Qwen99% / Llama90%, ASR0 within this controlled corpus. Read [method and limitations](docs/release/PI_RESULTS.md) before interpreting those numbers.

## Data, backups and artifacts

`scripts/seed-demo.py --out <NEW.sqlite3>` creates five synthetic customers and six months of activity without overwriting an existing target. The normal app migrates existing databases additively. `scripts/check-migrations.py` tests copies; the original DB files were not changed during implementation.

`scripts/backup.py` creates encrypted consistent snapshots and restores only to new paths, including per-DB MFA keys. Keep the backup encryption key separately. [Operator guide](docs/release/ADMIN_GUIDE.md) explains settings, reconciliation and research.

Historic milestones remain in `docs/`. Use `docs/release/STATUS.md` for the release record.
