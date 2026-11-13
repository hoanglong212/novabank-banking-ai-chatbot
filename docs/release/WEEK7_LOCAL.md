# Week 7 local deployment — 2026-11-05

- Application: http://127.0.0.1:8081
- Simulated mailbox: http://127.0.0.1:8081/outbox
- Staff assistant: http://127.0.0.1:8081/admin/assistant
- Separate agent: http://127.0.0.1:8094/health
- Alice: `alice` / `Alice@2026`; admin: `admin` / `Admin@2026`.

Both login MFA and transfer verification codes appear in the demo inbox. Choose the latest message of the appropriate kind. Codes are not included in transfer responses or chat.

This deployment uses `ENV=demo`, `LLM_PROVIDER=ollama`, `qwen2.5:7b` and the separate HTTP agent. The user authorized the model download. The original Ollama daemon could not see the model directory through its junction; a dedicated server at `127.0.0.1:11435` uses `D:\Ollama\models`. The existing daemon at port 11434 was left running.

Database: `.local/week7-deploy/novabank-v2.sqlite3`, copied with SQLite online backup from the dedicated fictional demo database (five customers, six months of transactions). Its MFA encryption key was copied alongside it. The older app on port 8080 and its database were left running because automatic approval review rejected stopping its process tree. Use port 8081 for the corrected savings trace behavior. Logs: `server-v2.log`, `server-v2-error.log`; launcher identity: `launcher-v2.pid`, all under `.local/week7-deploy/`.

After stopping the current launcher and its child processes, restart from the project directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-week7-local.ps1
```

The restart script reuses the dedicated Ollama server or starts the installed executable in a hidden window. It does not install a service, dependencies or model. Override `NOVABANK_OLLAMA_MODELS` if the model directory moves. Ctrl+C in the launching terminal stops the bank; the dedicated Ollama server remains available.

Banking and agent readiness returned HTTP 200. Chromium checks MFA sign-in and real Qwen calls for balance, staff user count and savings; the current results and origin are in `.local/week7-deploy/browser-check.json`. This is a functional check, not the complete Week 7 security evaluation. The start script successfully launched the new instance; stop/restart of an existing instance remains unverified.

This deployment does not mean the entire Week 7 research/evidence plan has passed acceptance. See `week7-evidence/PROGRESS.md`.
