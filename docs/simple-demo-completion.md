# Simple demo setup - completion evidence

Date: 19 October 2026. Scope: preserve the NovaBank protected chatbot and adapt
the supplied CTF template's startup and demo guidance, as clarified by the owner.

## Acceptance and evidence

| Acceptance criterion | Evidence |
| --- | --- |
| One URL serves frontend and backend | Native launcher tested on 8081/mock and 8080/Ollama; compiled HTML/assets and API returned successfully. |
| Model problems are actionable before presenting | Installed model preflight passed. An unreachable `OLLAMA_URL` caused nonzero launcher exit and `not_ready`; `.env` bytes were unchanged. |
| Offline demo stays usable | Mock mode passed balance, foreign-account denial, conversation isolation and dry-run checks without model calls. |
| Real model still works | Native Ollama acceptance returned `ollama_tool` for own balance and foreign-account denial. |
| Single container builds and runs | `docker build --no-cache -t novabank-demo .` passed; container acceptance checks passed on localhost:8082. |
| Container hygiene | Runtime UID 10001; no backend `.env` or frontend `node_modules` in final image; Docker health reported `healthy`. |
| Repeatable clean container run | Created disposable conversation, stopped `--rm` container, started a fresh instance, and verified an empty conversation list. |
| Authorization stays intact | Full backend suite: 58 passed, including 7 new setup/readiness cases. |

## Commands and results

- `.venv/Scripts/python.exe -m pytest -q` from `backend/`: **58 passed**.
  Existing Starlette/httpx deprecation warning remains.
- `npm run build` from `frontend/`, invoked by the launcher: **passed**.
  Existing Tailwind "No utility classes" warning remains; compiled CSS emitted.
- `npm run test:components` from `frontend/`: **6 checks passed**.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -CheckOnly`:
  **passed**, configured provider `ollama`, model `llama3.2:3b`.
- `scripts/run-demo.ps1 -Mode mock -Port 8081`: **passed**, build and live server.
- `scripts/run-demo.ps1 -Mode ollama -SkipBuild -Port 8080`: **passed**, live server.
- `backend/.venv/Scripts/python.exe scripts/check-demo.py http://127.0.0.1:8082 mock`:
  **passed** against the built container. The same acceptance checks passed
  against native mock and Ollama servers before promoting the check into `scripts/`.
- `docker build --no-cache -t novabank-demo .`: **passed**. An earlier interrupted
  build caused a Docker snapshot-cache failure; the uncached rebuild succeeded.
- `git diff --check`: **passed**.
- Browser identity regression: **not rerun**; it requires a dedicated Edge CDP
  session and the frontend identity implementation was unchanged. API isolation
  and existing component checks passed. No new visual design was introduced.
- Fresh-machine `-Setup` branch: **not independently exercised**; dependency
  installation commands were already verified during initial project setup.
- Docker-to-host Ollama networking: **documented but not tested**. Native Ollama
  is verified; Docker verification used mock mode.
- Independent review: **pending human review**; this was a single-agent implementation
  and verification pass, not an independent security audit.

## Changed files

- `backend/app/readiness.py`, `main.py`: optional model readiness endpoint.
- `backend/app/web.py`: optional compiled frontend hosting after API routes.
- `backend/tests/test_demo_setup.py`: readiness failures and static-serving boundaries.
- `scripts/run-demo.ps1`: shared setup/build/preflight/start launcher.
- `scripts/check-demo.py`: repeatable HTTP acceptance check with temporary conversations.
- `Dockerfile`, `.dockerignore`: single non-root application container.
- `README.md`, `.env.example`, `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`,
  `docs/SIMPLE_DEMO.md`: updated usage, limitations and architecture.

## Limits and rollback

The readiness endpoint checks model metadata, not successful generation, GPU
capacity or remote gateway availability. Docker mock/local mode is self-contained;
Ollama mode requires a host model service. Demo tokens and the proposed gateway
adapter remain prototype limitations. Python dependency ranges and base-image
tags are not immutable build locks.

The previous two-terminal Vite/FastAPI workflow remains available. Stop the new
launcher with Ctrl+C and omit `FRONTEND_DIST` to return to API-only serving. No
database migration was introduced and the user's `.env` was preserved. Temporary
HTTP-check conversations and the verification Docker container were removed.
The native Ollama demo on port 8080 was left available for review.
