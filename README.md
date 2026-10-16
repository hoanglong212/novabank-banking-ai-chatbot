# NovaBank Demo — Banking AI Customer Support Chatbot

A research **demo**, not a banking service. Built for Group 10's Runtime Security Gateway project (13–15 October 2026 scope).

**Main capabilities**

- React + TypeScript + Tailwind chat UI with a conversation sidebar and mobile layout.
- SQLite-persisted conversation history that survives refreshing and backend restarts.
- Multi-turn context passed to the agent; user conversations are separated by demo identity.
- An agent that can call four simulated banking tools.
- A **policy authorization point** that runs before tool execution; both ALLOW and DENY are audited.
- Two modes: `mock` for immediate offline functional demonstration; `ollama` for **guarded Llama 3.2 3B native tool proposals with application-bound inputs and replies**.
- Proposed adapter interface for the Group 10 gateway. This project **does not claim to have integrated the group's actual gateway**.

> **Safety notice:** Two demo tokens ship with the frontend; selecting a different user is possible. This is NOT real authentication, and it must not be exposed publicly or connected to actual banking APIs / customer PII. The local policy is a functional placeholder, NOT verified banking-grade security.

## 1. Requirements

- Python 3.11 or 3.12 recommended (3.13 also tested for backend here)
- Node.js 20.19+ or 22+
- npm
- Optional: [Ollama](https://ollama.com/) installed locally with `llama3.2:3b`

## 2. Quick start — Windows PowerShell

Open **Terminal 1** inside the extracted project:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` and `.\.venv\Scripts\python.exe -m pip` directly instead of changing execution policy.

Open **Terminal 2**:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. Choose demo **Minh Anh (Alice)** or **Gia Bảo (Bob)** from the sidebar. FastAPI docs: **http://127.0.0.1:8000/docs**.

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then run in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## 3. Turn on the real Ollama agent

`mock` is the initial mode: it makes the entire app usable **without** a downloaded AI model, but does **not** validate LLM reasoning quality. To run the guarded Ollama workflow:

```bash
ollama pull llama3.2:3b
ollama serve
```

If Ollama is already running as a background service, a second `ollama serve` is unnecessary.

Edit **backend/.env**:

```ini
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_URL=http://localhost:11434
```

**Restart FastAPI** after editing `.env`. Keep `GATEWAY_MODE=local` until you receive the real Group 10 gateway endpoint and API schema.

Llama 3.2 3B can have weaker Vietnamese/tool-choice accuracy than larger models. Test with the [demo scenarios](docs/DEMO_SCRIPT.md), not just one happy path. If Ollama cannot be reached, the backend returns an explicit 503 rather than silently faking a model response.

## 4. Four simulated tools

| Tool | Input | Description | Policy |
|---|---|---|---|
| `search_banking_faq` | `query` | Searches curated fictional-bank FAQ | Allow if valid |
| `get_account_balance` | Optional `account_id` | Returns the logged-in demo user's fictional balance | Must own account |
| `get_transaction_status` | `transaction_id` e.g. `TX-1002` | Looks up a fictional transaction | Must own transaction |
| `create_support_ticket` | `subject`, `description` | Adds a fictional ticket to local SQLite | Validation + allowlist |

Try Alice's balance `ACC-ALICE-001`, Alice transactions `TX-1001` and `TX-1002`, and Bob's transaction `TX-2001`. Alice must **not** be allowed to read `ACC-BOB-001` or `TX-2001`.

The right-side **Policy test** panel is **dry-run only**: it shows allow/deny decisions and logs them, but does not execute the banking tool. Real tool execution is shown when chat calls a tool and the policy returns ALLOW.

## 5. Useful API endpoints

```text
GET    /api/health
GET    /api/demo/users                    (DEMO ONLY)
GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/{id}/messages
POST   /api/conversations/{id}/messages
GET    /api/conversations/{id}/tool-events
DELETE /api/conversations/{id}
POST   /api/conversations/{id}/demo/tool-check     (DRY RUN)
```

Protected endpoints require `Authorization: Bearer demo-alice-token` (or Bob's **insecure demo token**). Conversation ownership is verified server-side; an ID alone cannot open someone else's history.

## 6. Run backend automated tests

From `backend/`:

```bash
python -m pytest -q
```

The suite includes chat persistence, two-user isolation, allowed/denied tools, authorization independent from model output, multi-turn mock context and fake Ollama protocol interactions.

## 7. Project layout

```text
banking-ai-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py          # HTTP endpoints, conversation ownership checks
│   │   ├── agent.py         # mock + Ollama multi-turn tool calling
│   │   ├── auth.py          # explicitly insecure demo identities
│   │   ├── config.py        # env config
│   │   ├── database.py      # SQLite history, tool events, support tickets
│   │   ├── faq.py           # synthetic FAQ knowledge base
│   │   ├── gateway.py       # demo policy + unintegrated remote adapter
│   │   ├── schemas.py       # request and tool argument validation
│   │   └── tools.py         # executor, tool contracts and auditing
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # UI and conversation operations
│   │   ├── api.ts           # backend client
│   │   ├── types.ts         # TypeScript API types
│   │   └── index.css       # UI styling
│   └── package.json
└── docs/
    ├── ARCHITECTURE.md
    ├── DEMO_SCRIPT.md
    └── SECURITY_AND_LIMITATIONS.md
```

## 8. Integration with Group 10 Gateway

The agent calls `ToolDispatcher.run` only. The dispatcher calls `PolicyGateway.authorize` **before** any tool function is dispatched. In remote mode it applies local validation/ownership checks first and then sends a request to a **proposed** `POST {GATEWAY_URL}/authorize` contract:

```json
{
  "principal_id": "alice",
  "conversation_id": "example-uuid",
  "tool_name": "get_account_balance",
  "arguments": {}
}
```

Expected remote reply shape: `{ "decision": "ALLOW" }` or `{ "decision": "DENY" }`. **This contract is a placeholder only**; adapt it after obtaining the actual API definition from the gateway developers. If configured remote gateway is missing, unavailable, or denies the request, the executor **fails closed**.

See [architecture](docs/ARCHITECTURE.md) and [security limits](docs/SECURITY_AND_LIMITATIONS.md).

## 9. What remains to finish in the next iteration

- Real identity provider/OIDC; do not deploy demo tokens.
- Wire in Group 10's real security gateway with contract tests.
- Measure tool-calling accuracy and Vietnamese conversational utility using real Ollama.
- Optionally add real token streaming/SSE (currently the UI shows a loading indicator while waiting for a complete reply).
- Improve KB retrieval and citations for actual bank-specific, approved policies.
- Run PII detector comparison and full round-trip gateway experiment as separate team tasks.

## Verification status

Verified locally on 16 October 2026: 49 backend tests passed; frontend production build passed; all 15 application scenarios passed against live Ollama and browser UI. Eight critical scenarios passed three runs each. See [completion and evidence](docs/reliability-completion.md), including limitations and the pending independent review.

The Ollama workflow selects a supported operation from user text, constrains native model proposals to it, binds IDs to user input, and formats authoritative tool results. This is a guarded hybrid application, not a benchmark of independent model reasoning. Unknown questions use curated FAQ retrieval. Model unavailability returns 503.

Message POST responses include `response_source`:

- `ollama_tool`: native proposal matches the application's selected operation and inputs.
- `ollama_tool_bound`: native proposal matches the selected tool; application replaces its arguments with user-bound inputs.
- `application_fallback`: missing or malformed native proposal; application executes its recognized operation through the authorization dispatcher.
- `application_template`: fixed application reply, without a tool execution.
- `mock`: separate scripted offline mode.

These labels describe orchestration; all Ollama-mode final replies are application-rendered. Labels are returned for the live response, not persisted on historical messages. The offline mock implementation is unchanged.

The frontend identity regression can be run with `npm run test:identity` from `frontend/` while frontend :5173, backend :8000, and an isolated Edge browser with remote debugging :9224 are running. It creates and removes its own temporary conversations.

This project is original implementation informed by official framework examples; it does not vendor or copy whole third-party repositories.
