# Running the bounded GĐ2 pilot

This uses the **legacy source-ingestion engine**, not the official real-API study. Read [PROTOCOL.md](PROTOCOL.md) and [INVENTORY.md](INVENTORY.md) first. Do not launch the full `research.run` matrix or the raw-results publisher for GĐ2.

Run from the repository root, using installed dependencies and both already-installed Ollama models:

```powershell
backend/.venv/Scripts/python.exe -m pytest research/tests -q
backend/.venv/Scripts/python.exe -m research.pilot
```

`--models qwen2.5:7b` or `--models llama3.1:8b` is available for a partial diagnostic pilot; label it partial. Default is both required models. This runner will not download models. It accepts only a local Ollama URL, creates a new disposable DB under `.local/research/pilot-gd2-*/sandbox`, and never accepts a demo DB path. It does not launch or change the demo backend. Do not use the demo UI concurrently for inference if measuring isolated model timing.

There are 72 primary observations (42 attack, 30 utility), plus six cached classifier calls. Raw observations, exact dataset, source hashes, model digests and timing summary remain in that ignored run directory. Each row has seed, temperature and an observation UUID; `trace_id` and `agent_run_id` are deliberately null because this engine never creates real agent runs. `mean_wall_ms` is measured including SQLite reset; `mean_logical_total_ms` adds the cached classifier cost to cases where D7 actually used it. The latter estimates uncached per-case work, not elapsed physical runtime. Generation token counts come from Ollama, with input/output separate. Do not call the legacy tool-selection score complete task utility.

## API preparation: no paid requests

An optional config template is at `research/.env.example`. Copy it to the root `.env` (already gitignored) only when needed; keep `<API_MODEL>` until the user chooses a provider/snapshot. Process environment overrides file values. Files are read without dotenv interpolation or exporting unrelated variables.

```powershell
backend/.venv/Scripts/python.exe -m research.api_adapter
```

This command only reports boolean configuration readiness/key presence and `network_calls: 0`. There is **no CLI option to make a live request**. The library's `ApiAdapter.complete()` is disabled by default. Future approved harness code must explicitly pass `allow_live=True`; merely putting a key in `.env` does not enable it. No real API call is part of GĐ2 tests; those use `httpx.MockTransport` and a synthetic fixture key.

The adapter accepts native Chat Completions `messages` (including properly linked `tool_call_id` values) and tool schemas. It returns normalized content/tool arguments, usage, latency, requested/returned model, response ID, fingerprint and requested/sent seed. It does not yet connect the banking agent's Ollama message format to the API; that multi-round integration belongs to GĐ3. It uses `max_completion_tokens`; a selected provider must pass a capability/conformance check for temperature, tools, seed support, token limits and usage fields before the official freeze. Unsupported seed is omitted and recorded, not silently claimed supported. Errors and redirects are not retried and do not print response bodies or keys.

## Git boundary

Before committing, inspect `git diff --cached --name-only` and staged content. Check `.env`, `.env.local`, `.local/research/` and log/DB paths with `git check-ignore`. Never force-add these paths. Keep all new raw JSONL/JSON, SQLite, screenshots, keys and operational logs in `.local`; only manually reviewed aggregate pilot numbers may be added to documentation. `.gitignore` is not a guarantee against intentional force-add or secret text pasted into another file. Historical synthetic release archives are separate and must not be republished as new evidence.

This phase commits locally only. No push, API spend or official experiment until the user's next authorization.
