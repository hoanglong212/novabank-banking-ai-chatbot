# NovaBank Banking Web App + AI Agent

A banking simulation and prompt-injection research project. React 19/Vite/TypeScript/Tailwind, FastAPI/SQLite, and a separate HTTP agent. All accounts and money are fictional.

| I want to… | Start here |
| --- | --- |
| Run a real Agent from a fresh clone | [Quick start with Docker](#quick-start-with-docker) |
| Give the team one URL they can open in a browser | [Host a shared HTTPS demo](docs/release/DEPLOYMENT.md#chia-sẻ-qua-https) |
| Develop the app on Windows | [Native Windows development](#native-windows-development) and the [frontend guide](frontend/README.md) |

## Quick start with Docker

Start Docker Desktop or Docker Engine with the `docker compose` command available. Run the following from a terminal:

```sh
git clone https://github.com/hoanglong212/novabank-banking-ai-chatbot.git
cd novabank-banking-ai-chatbot
docker compose -f compose.local.yaml up -d --build
```

Docker builds the web app and starts Bank, Agent and Ollama. The first run needs internet access and roughly 7 GB for model weights in addition to the images. Model weights and bank data are stored in separate Docker volumes. Docker is the only runtime you need to install for this path.

1. Open <http://127.0.0.1:8080> and sign in as `alice` with password `Alice@2026`.
2. On the verification screen, open the demo inbox and enter the sign-in code in the form.
3. In **Assistant**, ask **What is my account balance?**

Check model downloads with `docker compose -f compose.local.yaml logs models`. [Agent readiness](http://127.0.0.1:8080/api/ready) should show `"status": "ready"` and `"llm_provider": "ollama"`. Stop with `docker compose -f compose.local.yaml down`. After a pull, run `up -d --build` again with the same Compose file to rebuild using the existing volumes.

## Configuration files

| How you run | Template | Where to save your values |
| --- | --- | --- |
| Docker on your computer | [.env.example](.env.example) | Root `.env`, optional for port or model overrides |
| Shared HTTPS demo | [.env.hosted.example](.env.hosted.example) | Root `.env.hosted`, passed with `docker compose --env-file .env.hosted` |
| Local frontend using the shared server | [frontend/.env.example](frontend/.env.example) | `frontend/.env.local` with the team's API origin |
| Native Windows launcher | [backend/.env.example](backend/.env.example) | `backend/.env`, created by `-Setup` if absent |
| Optional research adapter | [research/.env.example](research/.env.example) | `research/.env`, supplied explicitly to the adapter |

With the shared HTTPS setup, one operator provisions the stack on a Linux server. Reviewers open the URL from an allowed network and use the same sign-in and Assistant steps. Their activity goes through one Bank API and one persistent DB. See the [shared database design](docs/release/SHARED_DATABASE.md) and [deployment guide](docs/release/DEPLOYMENT.md).

## Native Windows development

With Python, Node.js and Ollama installed, pull the models and run the Windows launcher:

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text:latest
ollama pull llama3.2:3b
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Setup -Mode ollama
# On later runs:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Mode ollama
```

Open <http://127.0.0.1:8080>. `-Setup` installs the app dependencies and creates `backend/.env` when needed. The launcher builds the frontend and runs Bank and Agent together. Ctrl+C stops both. For labeled offline responses, use `-Mode mock` and skip the Ollama steps.

Other synthetic logins include `bob / Bob@2026`, `charlie / Charlie@2026`, `support / Support@2026`, `operations / Operations@2026`, `auditor / Auditor@2026` and `admin / Admin@2026`. Staff logins always require email MFA or configured TOTP. Transfers always require OTP. Enter codes in the authentication form.

Use fictional data and keep hosted review on the configured reviewer network. Keep populated environment files and keys private.

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

CI runs these checks and a container smoke test with a real model. To verify the default model on a fresh demo, run `python scripts/smoke-agent.py --balance` from the repository root while the app is running on port 8080.

Measured research: 1,790 observations, zero execution errors, balanced sandbox journals. Defended utility Qwen99% / Llama90%, ASR0 within this controlled corpus. Read [method and limitations](docs/release/PI_RESULTS.md) before interpreting those numbers.

## Data, backups and artifacts

`scripts/seed-demo.py --out <NEW.sqlite3>` creates five synthetic customers and six months of activity without overwriting an existing target. The normal app migrates existing databases additively. `scripts/check-migrations.py` tests copies; the original DB files were not changed during implementation.

`scripts/backup.py` creates encrypted consistent snapshots and restores only to new paths, including per-DB MFA keys. Keep the backup encryption key separately. [Operator guide](docs/release/ADMIN_GUIDE.md) explains settings, reconciliation and research.

See the [release dossier](docs/release/README.md) for requirements, architecture, security results and demo materials.
