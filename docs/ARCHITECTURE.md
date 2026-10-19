# Architecture and data flow

```text
React + TypeScript UI
  -> FastAPI (authenticated demo principal from bearer token)
     -> SQLite (conversation ownership, messages, tool decisions, tickets)
     -> Agent (mock or Ollama /api/chat)
        -> Proposed tool name + validated arguments
           -> ToolDispatcher -> PolicyGateway.authorize(...) -> ALLOW/DENY audit
              -> On ALLOW only: simulated tool executor
              -> Tool result to Agent -> final assistant message
```

The `mock` agent chooses actions deterministically for offline demos; **it is not a generative AI**. In both modes, `bind_request` selects an operation and binds resource IDs to user input. With `LLM_PROVIDER=ollama`, one model request proposes a native tool call constrained to that operation. The application validates the proposal, audits mismatched tools, and executes at most one user-bound operation through the dispatcher. Missing or malformed proposals use the application fallback. Tool observations are rendered by the application, not passed back to the model. Up to the last 24 user/assistant messages are sent as context while full history remains in SQLite. `response_source` distinguishes native, rebound, fallback and template responses.

Development uses Vite on port 5173 and FastAPI on 8000. The demo launcher and Docker image set `FRONTEND_DIST` to the compiled UI directory so FastAPI serves both UI and API on one port. Static serving is registered after API routes and never exposes backend source or `.env`. `/api/health` is a liveness/configuration check; `/api/ready` checks that the configured Ollama model is installed and reachable (or reports ready immediately in mock mode). Readiness does not generate text, measure model quality, validate GPU capacity, or probe the remote policy gateway.

A dedicated `PolicyGateway` class decides, but does not execute tools. Local mode performs allowlist, schema, and ownership checks. Remote mode performs the same local checks and then sends an adapter request to a hypothetical `/authorize` endpoint; it FAILS CLOSED if remote gateway fails. The proposed API contract is NOT guaranteed to match Group 10's actual runtime security gateway.

Audit records ALLOW and DENY and whether execution happened. `demo/tool-check` evaluates policy but never executes, even for ALLOW. Frontend displays the latest events to help demonstrate decisions. No payment API, real customer records, real OTP, credential-handling or bank integration are implemented.
