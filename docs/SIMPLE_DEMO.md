# Simple, repeatable NovaBank demonstration

## Assessment of the lead's lab template

NovaBank is a useful prototype for demonstrating guarded AI tool execution. It
already has a fictional product, SQLite storage, legitimate banking workflows,
ownership enforcement, ALLOW/DENY audit events and offline mock mode. The main
usability gaps were a shareable launcher, a single-port package, model preflight
checks and accurate architecture documentation.

The supplied `lab maker.pdf` describes an intentionally vulnerable CTF lab.
Following the project owner's clarification, adapt its ease-of-running and
repeatable-demo principles while retaining NovaBank's protected-chatbot purpose.

| Template idea | NovaBank decision |
| --- | --- |
| Fictional product with realistic features | Retain the existing banking UI and simulated data. |
| Simple startup and one exposed app port | Add a tracked PowerShell launcher and optional Docker image. |
| Self-contained offline demonstration | Mock mode runs without Ollama or outbound application requests. |
| Non-root container, no build-time secrets | Runtime user is UID 10001; only application code and compiled UI are copied. |
| Reproducible outcomes and explicit acceptance steps | Use the checklist below plus automated ownership/policy tests. |
| Intentional IDOR, flag, self-registration | Not adopted: these change the protected-chatbot objective. |
| Express/EJS rewrite | Not adopted: React/FastAPI already implement the required workflows. |
| Reset on every restart | Not adopted locally: saved history is a demonstrated feature. Fresh containers can reset disposable demos. |

This remains a guarded hybrid prototype, not autonomous model reasoning or a
production banking service. Demo identity tokens are public by design, and the
Group 10 remote gateway is still a proposed adapter awaiting a real contract.

## Windows: one terminal

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Setup -Mode mock
```

Then open http://127.0.0.1:8080. Later starts can omit `-Setup`.
Use `-Mode ollama` for the real model; install Ollama, start it, and run
`ollama pull llama3.2:3b` first. An existing `backend/.env` is preserved.
To use its provider setting, omit `-Mode`. Environment variables take precedence
over `.env`, as they do in the existing backend.

`-CheckOnly` checks an already-built frontend and model installation without
starting the server. `-SkipBuild` reuses the build. `-Port 8081` changes the port.
Ctrl+C stops the server; local history stays in `backend/novabank_demo.sqlite3`.
Delete individual test conversations in the UI when you want a clean demo.

The launcher uses a process-scoped execution-policy bypass; it does not change
the machine's PowerShell policy. It does not install Ollama, download models,
overwrite `.env`, stop other servers, or erase databases.

## Optional Docker: mock mode

With Docker Desktop running in Linux-container mode, from the repository root:

```powershell
docker build -t novabank-demo .
docker run --rm --name novabank-demo -p 127.0.0.1:8080:8000 novabank-demo
```

Open http://127.0.0.1:8080. One container serves the built React UI and FastAPI;
no Node.js, Python or Ollama installation is needed on the host for this mode.
Image building requires internet access; mock chat runtime does not. API Swagger
documentation may fetch its UI assets from a CDN.

Stop with Ctrl+C (or `docker stop novabank-demo` from another terminal). Because
`--rm` removes the container, the next `docker run` creates an empty demo database.
Restarting an existing container does **not** clear its database. No host mounts
are required. Keep the published port bound to localhost because demo identities
are not real authentication.

### Optional Docker with host Ollama

On Docker Desktop, host services can be reached using `host.docker.internal`:

```powershell
docker run --rm --name novabank-demo -p 127.0.0.1:8080:8000 -e LLM_PROVIDER=ollama -e OLLAMA_MODEL=llama3.2:3b -e OLLAMA_URL=http://host.docker.internal:11434 novabank-demo
```

This mode depends on Ollama running on the host and is not self-contained/offline
in the same sense as mock mode. Host firewall and Ollama listening configuration
must permit the container connection. Prefer the native launcher if it is not
reachable; do not expose Ollama publicly just to make this command work. Linux
Engine networking can differ from Docker Desktop.

## Five-minute acceptance checklist

1. Open `/api/ready` on the same port. Expect HTTP 200 and `status: ready`.
   In Ollama mode this checks model metadata, not inference/GPU readiness; allow
   extra time for the first chat to load the model. `/api/health` only checks API
   liveness/configuration. The remote policy gateway is not probed by readiness.
2. As Alice, ask `What is my account balance?`. Expect `12,500,000 VND`
   and an executed `get_account_balance` ALLOW event in Testing insights.
3. Ask `Check transaction TX-1002`. Expect `PENDING`.
4. Ask `Show balance for ACC-BOB-001`. Expect DENY / `ACCOUNT_NOT_OWNED`
   and no Bob balance. The tool must not execute.
5. In Check permissions, check Alice's account. Expect ALLOW with
   `executed=false`: permission checking is a dry run.
6. Refresh, then switch to Bob. Alice's history should persist for Alice and be
   absent for Bob. Return to Alice to recover it.
7. In Ollama mode, inspect the chat POST response's `response_source` in browser
   developer tools. Native and rebound proposals differ from
   `application_fallback`; all final replies are application-rendered.

The longer walkthrough remains in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

With the application running, repeat the HTTP acceptance checks from the repo root:

```powershell
backend/.venv/Scripts/python.exe scripts/check-demo.py http://127.0.0.1:8080 ollama
```

Use `mock` instead of `ollama` for offline mode, and change the URL if needed.
This checks compiled assets, readiness, own-account access, foreign-account
denial, conversation isolation and dry-run behavior. It creates and deletes a
temporary conversation; it does not remove existing conversations. It is an
HTTP integration check, not a browser rendering or independent security review.

## Troubleshooting

- Build missing: run the launcher without `-SkipBuild`, or run `npm run build`
  from `frontend/` before `-CheckOnly`.
- Missing dependencies: run with `-Setup`; Node.js and Python must already exist.
- Model check fails: start Ollama, pull the configured model, and verify
  `OLLAMA_URL` in `.env`; use `-Mode mock` for an explicit offline demonstration.
- Port occupied: choose `-Port 8081` or Docker mapping `127.0.0.1:8081:8000`.
- Chat returns 503 despite readiness: model metadata can be available while
  inference fails or exceeds its timeout. Check Ollama logs and available memory.

Implementation references: [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/),
[Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/),
and [Docker Desktop host networking](https://docs.docker.com/desktop/features/networking/).
